"""
    Utility functions for scraping biorxiv
"""

import os.path
from contextlib import contextmanager
import requests
import re

import time
import random
import tempfile

def test_find_authors():
    assert find_authors('http://biorxiv.org/cgi/content/short/121814') == ['raul.peralta@uaem.mx']

def find_authors(url):
    """Retrieve page and capture author emails as strings
    """
    # url = 'http://biorxiv.org/cgi/content/short/{}.article-info'.format(code)
    url += '.article-info'
    page = requests.get(url)

    addrs = [m.replace('{at}', '@')
        for m in re.findall('.*\>(.*?\{at\}.*?)\<', page.text)]

    return list(set(addrs))


@contextmanager
def download_paper(url, timeout=10):
    """Downloads paper
    """

    # url = 'http://biorxiv.org/cgi/content/short/{}.pdf'.format(code)
    url = url + '.pdf'
    fn = os.path.join('data', os.path.basename(url))

    # with tempfile.NamedTemporaryFile(delete=False) as fh:
    with open(fn, 'wb') as fh:
        print('fetching %s into %s' % (url, fn))

        req = requests.get(url) #, timeout=timeout)
        fh.write(req.content)
        print('done fetching')

        time.sleep(0.05 + random.uniform(0,0.1))

    yield fn
