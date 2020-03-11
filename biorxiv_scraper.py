"""
    Utility functions for scraping biorxiv
"""

import os
import re
import importlib

# neither urllib nor requests play nicely with rq
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from bs4 import BeautifulSoup
    iiif_biorxiv = importlib.import_module('iiif-biorxiv.app')
except:
    print('Calculations will fail if this is a worker')

IIIF_HOST = os.environ.get('IIIF_HOST', 'iiif-biorxiv.saladi.org')

def baseurl(code):
    return 'https://www.biorxiv.org/content/10.1101/{}'.format(code)

def req(url):
    http = urllib3.PoolManager(cert_reqs='CERT_NONE', assert_hostname=False)
    page = http.request('get', url, timeout=120)
    return page.data.decode('utf-8')

def test_find_authors():
    assert find_authors('121814v1') == \
        {'all': ['raul.peralta@uaem.mx'], 'corr': ['raul.peralta@uaem.mx']}

re_at = re.compile('\{at\}')
def find_authors(code):
    """Retrieves page and captures author emails as list of strings
    """
    url = baseurl(code)
    page = req(url)
    soup = BeautifulSoup(page, 'lxml')
    addr = [t.attrs.get('content', None) 
            for t in soup.find_all("meta", {"name": "citation_author_email"})]
    
    # corresponding authors will have their email under another tag too
    corr = [t.find('a').attrs.get('href', None)
            for t in soup.find_all(None, {"class": "author-corresp-email-link"})]

    addr = [a for a in addr if a is not None]
    corr = [a.replace('mailto:', '') for a in corr if a is not None]

    return dict(corr=list(set(corr)), all=list(set(addr)))


def test_count_pages():
    assert count_pages('515643v1') == 43

re_pg = re.compile(r'Index \d+ out of bounds for length (\d+)')
def count_pages(paper_id):
    """cantaloupe iiif server returns the highest page index with an error
    if out of range is requested
    """
    url = "https://{}/iiif/2/biorxiv:{}.pdf/full/500,/0/default.jpg?page=1000"
    url = url.format(IIIF_HOST, paper_id)
    page = req(url)
    count = re_pg.findall(page)[0]
    return int(count)

def test_find_date():
    find_date("515643v1") == "2019-01-13"

def find_date(paper_id):
    url = "https://www.biorxiv.org/content/10.1101/{}".format(paper_id)
    page = req(url)
    soup = BeautifulSoup(page, 'lxml')

    text = soup.find_all("meta", {"name": "DC.Date"})[0]
    return text.attrs['content']

