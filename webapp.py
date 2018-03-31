"""Web app and utilities for rainbow colormap monitor
"""

import os
import os.path
import re
import sqlalchemy

from flask import Flask, render_template
# from flask_table import Table, Col
from flask_rq2 import RQ
from flask_mail import Message

import click
import tweepy

import pandas as pd

from models import db, Biorxiv, Test
from twitter_listener import StreamListener
from biorxiv_scraper import find_authors, download_paper
from detect_cmap import convert_to_img, parse_img, convert_to_jab, find_cm_dists, has_rainbow

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
app.config['MAIL_DEFAULT_SENDER'] = os.environ['MAIL_USERNAME']
# https://technet.microsoft.com/en-us/library/exchange-online-limits.aspx
# 30 messages per minute rate limit
# app.config['MAIL_MAX_EMAILS'] = 30

app.config['WEB_PASSWORD'] = os.environ['WEB_PASSWORD']

# class PapersTable(Table):
#     text = Col('Text')
#     user_name = Col('User name')
#     created = Col('Created')
#     parse_status = Col('Parse status')


@app.route('/')
def webapp():
    """Renders the website with current results
    """
    papers = Biorxiv.query.all()
    return papers
    # table = PapersTable(papers)
    # return table.__html__()
    return render_template('main.html')


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


@app.cli.command()
@click.option('--test', is_flag=True)
def monitor_biorxiv(test):
    """Starts the twitter listener on the command line,
       writes tweets to the database,
       dispatches a processing job to the processing queue (rq)
    """

    auth = tweepy.OAuthHandler(
        app.config['TWITTER_APP_KEY'], app.config['TWITTER_APP_SECRET'])
    auth.set_access_token(
        app.config['TWITTER_KEY'], app.config['TWITTER_SECRET'])
    api = tweepy.API(auth)

    if test:
        def insert_db(**kwargs):
            obj = Test(**kwargs)
            db.session.add(obj)
            db.session.commit()
            return

        stream_listener = StreamListener(insert_db)
        stream = tweepy.Stream(auth=api.auth, listener=stream_listener,
            trim_user='True', include_entities=True, tweet_mode="extended")
        stream.filter(track=["clinton", "sanders"])
    else:
        def insert_db(**kwargs):
            obj = Biorxiv(**kwargs)
            db.session.add(obj)
            db.session.commit()
            return

        stream_listener = StreamListener(insert_db)
        stream = tweepy.Stream(auth=api.auth, listener=stream_listener,
            trim_user='True', include_entities=True, tweet_mode="extended")
        stream.filter(follow=['biorxivpreprint'])

    return


@app.cli.command()
def retrieve_timeline():
    """Picks up current timeline (for testing),
       writes tweets to the database,
       dispatches a processing job to the processing queue (rq)
    """

    auth = tweepy.OAuthHandler(
        app.config['TWITTER_APP_KEY'], app.config['TWITTER_APP_SECRET'])
    auth.set_access_token(
        app.config['TWITTER_KEY'], app.config['TWITTER_SECRET'])
    api = tweepy.API(auth)

    def insert_db(**kwargs):
        obj = Test(**kwargs)
        db.session.merge(obj)
        db.session.commit()
        return obj

    for t in api.user_timeline(screen_name='biorxivpreprint', trim_user='True',
            include_entities=True, tweet_mode="extended"):
        text = re.sub(r'[^\x00-\x7f]',r'', t.full_text)
        print(t.full_text)
        dbobj = insert_db(id=t.id,
                      user_id=t.user.id,
                      created=t.created_at,
                      text=text)

        url = t.entities['urls'][0]['expanded_url']
        process_paper.queue(dbobj, url)

    return


@rq.job(timeout='10m')
def process_paper(dbobj, url):
    """Processes paper starting from url/code

    1. download paper
    2. check for rainbow colormap
    3. if rainbow, get authors
    4. update database entry with colormap detection and author info
    """

    with download_paper(url) as fn:
        df = pd.concat([parse_img(p) for p in convert_to_img(fn)],
            ignore_index=True, copy=False)

        # Write out RGB colors found
        name, _ = os.path.splitext(fn)
        df.to_csv(name + '_colors.csv', index=False)


        # Find nearest color for each page
        df = convert_to_jab(df)
        df_cmap = df.groupby('fn').apply(find_cm_dists)

        # filter output before writing
        df_cmap = df_cmap[df_cmap['pct_cm'] > 0.5]
        df_cmap.to_csv(name + '_cm.csv')

        if has_rainbow(df_cmap):
            authors = find_authors(url)
        else:
            authors = ''

        # update database
        dbobj.parse_status = authors
        db.session.commit()

        return
