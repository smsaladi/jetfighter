"""
    Utility functions for scraping biorxiv
"""

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

def baseurl(code):
    return 'https://www.biorxiv.org/content/10.1101/{}'.format(code)

def req(url):
    http = urllib3.PoolManager()
    page = http.request('get', url, timeout=120)
    return page.data.decode('utf-8')

def test_find_authors():
    assert find_authors('121814') == \
        {'all': ['raul.peralta@uaem.mx'], 'corr': ['raul.peralta@uaem.mx']}

re_at = re.compile('\{at\}')
def find_authors(code):
    """Retrieves page and captures author emails as list of strings
    """
    url = baseurl(code) + '.article-info'
    page = req(url)
    soup = BeautifulSoup(page, 'lxml')

    addr = soup(text=re_at)
    addr = [t.replace('{at}', '@') for t in addr]

    # corresponding authors will have their email listed in more than 1 place
    corr = list(set([x for x in addr if addr.count(x) > 1]))
    # if not, use the last author
    if not corr:
        corr = [addr[-1]]

    return dict(corr=corr, all=list(set(addr)))


def test_count_pages():
    assert count_pages('515643v1') == 44

re_pg = re.compile(r'Index \d+ out of bounds for length (\d+)')
def count_pages(paper_id):
    """cantaloupe iiif server returns the highest page index with an error
    if out of range is requested
    """
    url = "https://iiif-biorxiv.saladi.org/iiif/2/biorxiv:{}.full.pdf/full/500,/0/default.jpg?page=1000"
    url = url.format(paper_id)
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
