README
======

Scientists co-opt our visual system to convey numerical data in a format that's easily understandable using spatial and color variation to capture details of the underlying data. A “colormap” transforms the set of numbers into a pattern of plotted colors. 

When done poorly, this transformation introduces well-established visual artifacts and obscures the underlying detail. Furthermore, certain colormaps create images that are inaccessible to readers with anomalous color vision (i.e. colorblindness). 

Unfortunately, widely-used rainbow colormaps, like "jet", face these issues but are pervasive in the scientific literature. Jetfighter aims to prevent this by detecting problematic colormaps in publically available pre-print manuscripts and then contacting the authors, if necessary. 

Explore recently screened manuscripts here, and check out a companion website that provides a solution for published figures, [fixthejet.caltech.edu](fixthejet.caltech.edu), as well!


## To-do 
(a wishlist we may never get to...)

* Monitor arxiv feed (make a list of other preprint servers)
* Check detection code and data saved into database
* Some heuristic for red/green used together? in addition to rainbow colormaps?
* Write tests for cmap detection code
* Current pending count

## Other notes

Worker non-pip dependencies
    - [poppler](https://poppler.freedesktop.org/) for `pdftoppm`

* a number of config vars need to be in `.env` and are handled on Heroku with [heroku-config](https://github.com/xavdid/heroku-config)

* some jobs can take a long time, so we adjust `timeout` to `30m`. Also, make sure that `wait_timeout` on the mysql database is sufficiently large (e.g. `28800` seconds)

```shell
heroku config:push -o #  Writes the contents of a local file into heroku config (-o overwrites)
heroku config:pull # Writes the contents of heroku config into a local file
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

2. Configure a cronjob to monitor feed (e.g. `crontab -e`, below for every 20 minutes)
```shell
*/20 * * * * FLASK_APP=~/github/jetfighter/webapp.py /home/saladi/anaconda3/bin/flask retrieve_timeline >> ~/logs/jetfighter_retrieve.cron.log
```

3. Test/start frontend (in practice, runs on Heroku)
```shell
FLASK_APP=webapp.py flask run
```
