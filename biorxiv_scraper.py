"""
    Utility functions for scraping biorxiv
"""

import os.path
from contextlib import contextmanager
import requests
import re

import time
import random

def baseurl(code):
    return 'http://biorxiv.org/cgi/content/short/{}'.format(code)

def test_find_authors():
    assert find_authors('121814') == \
        {'all': ['raul.peralta@uaem.mx'], 'corr': ['raul.peralta@uaem.mx']}

def find_authors(code):
    """Retrieves page and captures author emails as list of strings
    """
    url = baseurl(code) + '.article-info'
    page = requests.get(url)

    def re_email(r):
        return [m.replace('{at}', '@') for m in re.findall(r, page.text)]

    addrs = re_email('.*\>(.*?\{at\}.*?)\<')
    corr = re_email('Corresponding author.*>(.*\{at\}.*?)<.*')

    return dict(corr=corr, all=list(set(addrs)))

def download_paper(code, outdir, timeout=10, debug=False):
    """Downloads paper and returns filename
    """
    url = baseurl(code) + '.pdf'
    fn = os.path.join(outdir, os.path.basename(url))

    with open(fn, 'wb') as fh:
        if debug:
            print('Fetching %s into %s' % (url, fn))

        req = requests.get(url, timeout=timeout)
        fh.write(req.content)

        time.sleep(0.05 + random.uniform(0, 0.1))

    return fn
