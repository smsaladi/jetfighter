README
======

Need to --

* Monitor arxiv feed (make a list of other preprint servers)
* Check detection code and data saved into database
* Datatable view (color by status)
* Admin view
    - code to compose email
    - code to rerun job
* Write tests for cmap detection code
* Integrate with travis

Worker non-pip dependencies
    - [poppler](https://poppler.freedesktop.org/) for `pdftoppm`

* env vars handling using [heroku-config](https://github.com/xavdid/heroku-config)

```shell
heroku config:push -o #  Writes the contents of a local file into heroku config (-o overwrites)
heroku config:pull # Writes the contents of heroku config into a local file
```

* Put private info into environment (bash-like shells)

```shell
sed -e '/^$/d' -e '/^#/d' -e 's/^/export /' .env | source /dev/stdin
```

* For testing of twitter feed listener (only):

```shell
# insert sample entries and start jobs
FLASK_APP=webapp.py flask retrieve_timeline

# test out streaming (but dont start jobs)
FLASK_APP=webapp.py flask monitor_biorxiv --test
```

* Workers should have all requirements installed
```shell
pip install -r requirements.txt
pip install -r requirements_worker.txt
```

1. Start backend worker(s)

```shell
FLASK_APP=webapp.py flask rq worker
```

2. Start twitter follower (only one!!) -- should always be running

```shell
FLASK_APP=webapp.py flask monitor_biorxiv
```

3. Start frontend (runs with heroku)

```shell
FLASK_APP=webapp.py flask run
```
