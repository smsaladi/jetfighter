README
======

Need to --

* Monitor biorxiv and arxiv feeds
* Update database with new items and add jobs to queue
* Website to display database and job status (?)
* Code to lift author information from preprint site?
-- code to compose email?

Dependencies
    - [poppler](https://poppler.freedesktop.org/) for `pdftoppm`

* env vars handling using [heroku-config](https://github.com/xavdid/heroku-config)

```shell
heroku config:push -o #  Writes the contents of a local file into heroku config (-o overwrites)
heroku config:pull # Writes the contents of heroku config into a local file
```

* Testing only

```shell
# insert sample entries and start jobs
FLASK_APP=webapp.py flask retrieve_timeline

# test out streaming (but dont start jobs)
FLASK_APP=webapp.py flask monitor_biorxiv --test
```

1. Start backend worker(s)

```shell
FLASK_APP=webapp.py flask rq worker
```

2. Start twitter follower (only one!!)

```shell
FLASK_APP=webapp.py flask monitor_biorxiv
```

3. Start frontend

```shell
FLASK_APP=webapp.py flask run
```
