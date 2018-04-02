"""Web app and utilities for rainbow colormap monitor
"""

import os
import os.path
import re
import tempfile

from flask import Flask, render_template
from flask_rq2 import RQ
from flask_mail import Message
from sqlalchemy import desc

import click
import tweepy

import pytest

from models import db, Biorxiv, Test
from twitter_listener import StreamListener
from biorxiv_scraper import find_authors, download_paper
from detect_cmap import detect_rainbow_from_file


app = Flask(__name__)

# For data storage
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['SQLALCHEMY_DATABASE_URI']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db.init_app(app)

# For job handling
app.config['RQ_REDIS_URL'] = os.environ['RQ_REDIS_URL']
rq = RQ(app)

# For monitoring papers (until Biorxiv provides a real API)
app.config['TWITTER_APP_KEY'] = os.environ['TWITTER_APP_KEY']
app.config['TWITTER_APP_SECRET'] = os.environ['TWITTER_APP_SECRET']
app.config['TWITTER_KEY'] = os.environ['TWITTER_KEY']
app.config['TWITTER_SECRET'] = os.environ['TWITTER_SECRET']

# for author notification
app.config['MAIL_SERVER'] = 'smtp.office365.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ['MAIL_USERNAME']
app.config['MAIL_PASSWORD'] = os.environ['MAIL_PASSWORD']
app.config['MAIL_DEFAULT_SENDER'] = os.environ['MAIL_DEFAULT_SENDER'].replace("'", "")
# https://technet.microsoft.com/en-us/library/exchange-online-limits.aspx
# 30 messages per minute rate limit
app.config['MAIL_MAX_EMAILS'] = 30

app.config['WEB_PASSWORD'] = os.environ['WEB_PASSWORD']

app.config['DEBUG'] = os.environ.get('DEBUG')


tweepy_auth = tweepy.OAuthHandler(
    app.config['TWITTER_APP_KEY'], app.config['TWITTER_APP_SECRET'])
tweepy_auth.set_access_token(
    app.config['TWITTER_KEY'], app.config['TWITTER_SECRET'])
tweepy_api = tweepy.API(tweepy_auth)


@app.route('/')
def webapp():
    """Renders the website with current results
    """
    papers = (Biorxiv.query
                     .order_by(desc(Biorxiv.created))
                     .limit(50)
                     .all())
    return render_template('main.html', papers=papers)

@app.route('/result/<string:paper_id>')
def show_results(paper_id):
    """Have a buttons to resubmit job, modify email, and queue for send now/later
    """
    record = Biorxiv.query.filter_by(id=paper_id).first()
    if not record:
        return render_template('result.html', table='Paper not found')
    #     testq = rq.Queue('testq', async=False)
    html = record.parse_data.to_html(bold_rows=False, index=False, border=0)
    return render_template('result.html', table=html)


def webauth():
    """Allows for login support
    """
    return render_template('auth.html')


def send_email():
    """Provides html snippet for sending email
    """
    msg = Message("Hello",
                  sender="from@example.com",
                  recipients=["to@example.com"])
    return render_template('email.html')


def parse_tweet(t, db=db, objclass=Biorxiv, verbose=True):
    """Parses tweets for relevant data,
       writes each paper to the database,
       dispatches a processing job to the processing queue (rq)
    """
    try:
        text = t.extended_tweet["full_text"]
    except AttributeError:
        pass

    try:
        text = t.full_text
    except AttributeError:
        text = t.text

    if verbose: 
        print(t.id_str, text[:25], end='\r')
    if not db:
        return
 
    try:
        url = t.entities['urls'][0]['expanded_url']
        code = os.path.basename(url)
    except:
        print('Error parsing url/code from tweet_id', t.id_str)
        return

    try:
        title = re.findall('(.*?)\shttp', text)[0]
    except:
        # keep ASCII only (happens with some Test tweets)
        title = re.sub(r'[^\x00-\x7f]', r'', text)

    obj = objclass(
        id=code,
        created=t.created_at,
        title=title,
    )

    db.session.merge(obj)
    db.session.commit()

    process_paper.queue(obj)


@app.cli.command()
@click.option('--test', is_flag=True) 
def monitor_biorxiv(test):
    """Starts the twitter listener on the command line
    """
    if test:
        filter_args = dict(track=['clinton', 'sanders'])
        stream_listener = StreamListener(lambda t: parse_tweet(t, db=None))
    else:
        filter_args = dict(follow=['biorxivpreprint'])
        stream_listener = StreamListener(parse_tweet)

    stream = tweepy.Stream(auth=tweepy_api.auth, listener=stream_listener,
            trim_user='True', include_entities=True, tweet_mode='extended')
    stream.filter(**filter_args)
 

@app.cli.command()
def retrieve_timeline():
    """Picks up current timeline (for testing)
    """
    for t in tweepy_api.user_timeline(screen_name='biorxivpreprint', count=1000,
            trim_user='True', include_entities=True, tweet_mode='extended'):
        parse_tweet(t)

@app.cli.command()
@click.argument('ids', nargs=-1)
def resubmit_job(ids):
    """Picks up current timeline (for testing)
    """
    for i in ids:
        rec = Biorxiv.query.filter_by(id=i).first()
        if rec:
            process_paper.queue(rec)
        else:
            print("id not yet in database")


@rq.job(timeout='10m')
def process_paper(obj):
    """Processes paper starting from url/code

    1. download paper
    2. check for rainbow colormap
    3. if rainbow, get authors
    4. update database entry with colormap detection and author info
    """

    with tempfile.TemporaryDirectory() as td:
        fn = download_paper(obj.id, outdir=td)
        obj.parse_status, obj.parse_data = detect_rainbow_from_file(fn)
        if obj.parse_status:
            obj.author_contact = find_authors(obj.id)
        db.session.merge(obj)
        db.session.commit()

## NOTE: NEEDS WORK
@pytest.fixture()
def test_setup_cleanup():
    # should only be one, but... just in case
    for obj in Test.query.filter_by(id='172627v1').all():
        db.session.delete(obj)
    db.session.commit()

    # Delete temporary row
    for obj in Test.query.filter_by(id='172627v1').all():
        db.session.delete(obj)
    db.session.commit()

def test_integration(test_setup_cleanup):
    """Submit job for known jet colormap. Remove from database beforehand.
    Write to database.
    Check for written authors.
    """

    testq = rq.Queue('testq', async=False)

    preobj = Test(id='172627v1')
    testq.enqueue(process_paper, preobj)

    postobj = Test.query.filter_by(id='172627v1').first()

    # check that document was correctly identified as having a rainbow colormap
    assert postobj.parse_status

    # check that authors were correctly retrieved
    authors = postobj.author_contact
    assert authors['corr'] == ['t.ellis@imperial.ac.uk']
    assert set(authors['all']) == set([
        'o.borkowski@imperial.ac.uk', 'carlos.bricio@gmail.com',
        'g.stan@imperial.ac.uk', 't.ellis@imperial.ac.uk'])
