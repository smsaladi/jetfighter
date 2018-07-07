"""Web app and utilities for rainbow colormap monitor
"""

import os
import os.path
import re
import math
import tempfile
import base64

import flask
from flask import Flask, render_template
from flask_rq2 import RQ
from flask_mail import Message
from flask_wtf.csrf import CSRFProtect, CSRFError

from sqlalchemy import desc

import click
import tweepy

import pytest

from models import db, Biorxiv, Test
from twitter_listener import StreamListener
from biorxiv_scraper import find_authors, download_paper
from detect_cmap import convert_to_img, detect_rainbow_from_file

import utils

# Reads env file into environment, if found
_ = utils.read_env()

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

app.config['DEBUG'] = os.environ.get('DEBUG')

app.config['WEB_PASSWORD'] = os.environ['WEB_PASSWORD']

app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
csrf = CSRFProtect(app)

tweepy_auth = tweepy.OAuthHandler(
    app.config['TWITTER_APP_KEY'], app.config['TWITTER_APP_SECRET'])
tweepy_auth.set_access_token(
    app.config['TWITTER_KEY'], app.config['TWITTER_SECRET'])
tweepy_api = tweepy.API(tweepy_auth)


@app.route('/')
def home():
    """Renders the website with current results
    """

    cats = flask.request.args.get('categories')
    if cats:
        cats = [int(x) for x in cats.split(',')]
    else:
        cats = [-1, 0, 1]

    papers = (Biorxiv.query
                     .filter(Biorxiv.parse_status.in_(cats))
                     .order_by(desc(Biorxiv.created))
                     .limit(500)
                     .all())

    rerun = flask.request.args.get('rerun')
    if rerun:
        if flask.session.get('logged_in'):
            if rerun == 'all':
                jobs_queued = 0
                for p_obj in papers:
                    process_paper.queue(p_obj)
                    jobs_queued += 1
                flask.flash("{} jobs have been queued. "
                            "Make sure rq workers are running".format(jobs_queued))
            else:
                flask.flash("Sorry, only rerun='all' is implemented right now")
        else:
            flask.flash("Sorry, you need to login to do that!")

    return flask.render_template('main.html', papers=papers)

@app.route('/pages/<string:paper_id>')
def pages(paper_id, prepost=1, maxshow=10):
    """Returns base64 encoded image intended for ajax calls only
    1-index I think...
    """
    record = Biorxiv.query.filter_by(id=paper_id).first()
    if not record:
        return flask.jsonify({})

    pages = record.pages

    # find pages before and after (requested or default)
    try:
        prepost = math.fabs(int(flask.request.args.get('prepost')))
    except:
        pass

    # find pages before and after (requested or default)
    try:
        maxshow = math.fabs(int(flask.request.args.get('maxshow')))
    except:
        pass

    show_pgs = {}
    if pages:
        # add all detected pages up to maxshow count
        show_pgs = {i:True for i in pages[:maxshow]}
        # pad with undetected pages
        for i in pages:
            for j in range(i - prepost, i + prepost + 1):
                if len(show_pgs) < maxshow:
                    if j not in pages:
                        show_pgs[j] = False
                else:
                    return flask.jsonify(show_pgs)
    else:
        show_pgs = {i:False for i in range(1, maxshow + 1)}

    return flask.jsonify(show_pgs)

@app.route('/preview/<string:paper_id>/<int:pg>')
def preview(paper_id, pg):
    """Returns base64 encoded image intended for ajax calls only
    """
    img_data = None

    # download and convert paper to images
    # delete those pages that aren't shown
    pdf_fn = "static/previews/{}.pdf".format(paper_id)
    if not os.path.exists(pdf_fn):
        pdf_fn = download_paper(paper_id, "static/previews/")

    show_fn = []
    for pg_fn in convert_to_img(pdf_fn, outdir='static/previews/', format='jpeg',
        other_opt=['-f', str(pg), '-l', str(pg), '-jpegopt', 'quality=50,progressive=y', '-scale-to', '350']):
        if re.match(".*\-0*{}".format(pg), pg_fn):
            with open(pg_fn, "rb") as fh:
                img_data = fh.read()
            break

    b64img = 'data:image/jpg;base64,' + base64.b64encode(img_data).decode("utf-8")

    return flask.jsonify(b64img)
# flask.render_template('preview_img.html', b64img=b64img)

@app.route('/result/<string:paper_id>')
def show_results(paper_id, prepost=1, maxshow=10):
    """Have a buttons to resubmit job, modify email, and queue for send now/later
    """
    record = Biorxiv.query.filter_by(id=paper_id).first()
    if not record:
        return render_template('result.html', table='Paper not found')
    html = record.parse_data.to_html(bold_rows=False, index=False, border=0)
    pages = record.pages

    # find pages before and after (requested or default)
    try:
        prepost = math.fabs(int(flask.request.args.get('prepost')))
    except:
        pass

    if len(pages) > 0:
        # need to somehow keep information the pages being shown
        show_pgs = set()
        for i, num in enumerate(pages):
            # if number of pages to go + current show pages is greater than maxshow,
            # then don't add prepost
            if len(show_pgs) + len(pages) - i + 1 < maxshow:
                show_pgs.update(range(num-prepost, num+prepost))
            else:
                show_pgs.add(num)
            # if we exceed maxshow, then no more
            if len(show_pgs) > maxshow:
                break
    else:
        show_pgs = set(range(1, maxshow + 1))

    # download and convert paper to images
    # delete those pages that aren't shown
    pdf_fn = "static/previews/{}.pdf".format(paper_id)
    if not os.path.exists(pdf_fn):
        pdf_fn = download_paper(paper_id, "static/previews/")

    show_fn = []
    # pdftoppm -jpeg -jpegopt quality=75,progressive=y -scale-to 350
    for pg_fn in convert_to_img(pdf_fn, outdir='static/previews/', format='jpeg',
        other_opt=['-jpegopt', 'quality=50,progressive=y', '-scale-to', '350']):
        pg_num = pg_fn.rsplit('-', maxsplit=1)[1].split('.')[0]
        if int(pg_num) in show_pgs:
            show_fn.append(flask.url_for('static', filename=pg_fn.replace('static/', '')))
        #else:
        #    os.unlink(pg_fn)

    # os.unlink(pdf_fn)

    # display images
    return flask.render_template('result.html', imgs=show_fn, table=html)

@app.route('/notify/<string:paper_id>', methods=['POST'])
@app.route('/notify/<string:paper_id>/<int:force>', methods=['POST'])
def notify_authors(paper_id, force=0):
    if flask.session.get('logged_in'):
        record = Biorxiv.query.filter_by(id=paper_id).first()
        if not record:
            return flask.jsonify(result=False, message="paper not found")

        try:
            corr = record.author_contact.get('corr')
        except:
            noemail = True

        if noemail or corr is None or '@' not in corr:
            return flask.jsonify(result=False,
                message="mangled or missing email addresses")

        if force != 1 and record.email_sent == 1:
            return flask.jsonify(result=False,
                message="email already sent. must use force=1 to send another")

        if len(request.form['message']) < 50:
            return flask.jsonify(result=False,
                                 message="POST missing message")

        msg = Message(
            "Biorxiv Manuscript {}: Colormap suggestion".format(record.id),
            sender="saladi@caltech.edu",
            recipients=[corr])
        msg.body = request.form['message']
        mail.send(msg)

        return flask.jsonify(result=True, message="successfully sent")
    else:
        return flask.jsonify(result=False, message="not logged in")

@app.route('/rerun/<string:paper_id>', methods=['POST'])
def rerun_web(paper_id):
    if flask.session.get('logged_in'):
        rec = Biorxiv.query.filter_by(id=paper_id).first()
        if not rec:
            return flask.jsonify(result=False, message="paper not found")
        process_paper.queue(rec)
        return flask.jsonify(result=True, message="successfully sent")
    else:
        return flask.jsonify(result=False, message="not logged in")

@app.route('/login', methods=['GET', 'POST'])
def admin_login():
    if flask.request.method == 'GET':
        if flask.session.get('logged_in'):
            flask.flash('You are already logged in!')
            return flask.redirect('/')
        return flask.render_template('login.html')

    if flask.request.form['password'] == app.config['WEB_PASSWORD']:
        flask.session['logged_in'] = True
    else:
        flask.flash('wrong password!')
        return flask.render_template('login.html')

    return flask.redirect('/')

@app.route('/logout', methods=['GET'])
def logout():
    logged_in = flask.session.get('logged_in')
    flask.session.clear()
    if logged_in:
        flask.flash("You have been successfully logged out")
    else:
        flask.flash("Not logged in! (but the session has been cleared)")
    return redirect('/')

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    flask.flash('CSRF Error. Try again?')
    return flask.redirect(flask.url_for('admin_login'))


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

    obj = db.session.merge(obj)
    db.session.commit()

    # don't reprocess papers that have already been entered
    if obj.title is None:
        process_paper.queue(obj)


# @app.cli.command()
# @click.option('--test', is_flag=True)
# def monitor_biorxiv(test):
#     """Starts the twitter listener on the command line
#     """
#     if test:
#         filter_args = dict(track=['clinton', 'sanders'])
#         stream_listener = StreamListener(lambda t: parse_tweet(t, db=None))
#     else:
#         # user_id for 'biorxivpreprint'
#         filter_args = dict(follow=['1949132852'])
#         stream_listener = StreamListener(parse_tweet)

#     stream = tweepy.Stream(auth=tweepy_api.auth, listener=stream_listener,
#             trim_user='True', include_entities=True, tweet_mode='extended')
#     stream.filter(**filter_args)


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
        obj.pages, obj.parse_data = detect_rainbow_from_file(fn)
        if len(obj.pages) > 0:
            obj.parse_status = 1
            obj.author_contact = find_authors(obj.id)
        else:
            obj.parse_status = 0
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

@app.cli.command()
@click.argument('paper_id', required=False)
def rerun(paper_id=None):
    """Rerun some or all papers in database
    """
    n_queue = 0
    if paper_id:
        rec = Biorxiv.query.filter_by(id=paper_id).first()
        if rec:
            process_paper.queue(rec)
            n_queue += 1
        else:
            print("paper_id {} not found".format(paper_id))
    else:
        for rec in Biorxiv.query.all():
            process_paper.queue(rec)
            n_queue += 1

    print("Queued {} jobs".format(n_queue))
    return

if __name__ == "__main__":
    app.run(debug=True, threaded=True, use_reloader=False)
