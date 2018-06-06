"""
    Utility functions for scraping biorxiv
"""

import os.path
import time
import random
import re

import requests

try:
    from bs4 import BeautifulSoup
except:
    print('Calculations will fail if this is a worker')

def baseurl(code):
    return 'http://biorxiv.org/cgi/content/short/{}'.format(code)

def test_find_authors():
    assert find_authors('121814') == \
        {'all': ['raul.peralta@uaem.mx'], 'corr': ['raul.peralta@uaem.mx']}

def find_authors(code):
    """Retrieves page and captures author emails as list of strings
    """
    url = baseurl(code) + '.article-info'
    page = requests.get(url, timeout=60)
    soup = BeautifulSoup(page.text, 'lxml')

    addr = soup(text=re.compile('\{at\}'))
    addr = [t.replace('{at}', '@') for t in addr]

    # corresponding authors will have their email listed in more than 1 place
    corr = list(set([x for x in addr if addr.count(x) > 1]))
    # if not, use the last author
    if not corr:
        corr = [addr[-1]]

    return dict(corr=corr, all=list(set(addr)))

def download_paper(code, outdir, timeout=60, debug=False):
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
