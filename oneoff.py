"""
Maintainance tasks that have needed to be done in the past
Mainly for reference

run as: FLASK_APP=oneoff.py flask add_posted_dates
"""

import click
from tqdm import tqdm

from sqlalchemy import desc

from models import Biorxiv
from webapp import app, rq, db, process_paper
from biorxiv_scraper import find_date

@app.cli.command()
def add_posted_dates():
    """Add dates to entries in database
    updating the most recent first
    """
    records = (Biorxiv.query
                      .filter_by(posted_date="")
                      .order_by(desc(Biorxiv.created))
                      .all()[:10])
    for r in tqdm(records):
        print(r.title)
        r.posted_date = find_date(r.id)
        db.session.merge(r)
        db.session.commit()
        
    return

@app.cli.command()
@click.option('--head', default=None)
@click.option('--now', is_flag=True)
def rerun_missing(head=None, now=False):
    """Run unparsed papers
    """
    query = Biorxiv.query.filter_by(parse_status=0)
    if head:
        query = query.limit(head)
    elif now:
        raise ValueError("Running everything now will be a headache!")
    else:
        query = query.all()
    
    for rec in tqdm(query):
        if now:
            process_paper(rec)
        else:
            process_paper.queue(rec)
    return 

@app.cli.command()
@click.argument('paper_ids', nargs=-1)
@click.option('--now', is_flag=True)
def rerun():
    n_queue = 0
    for p in paper_ids:
        if now:
            rec = Biorxiv.query.filter_by(id=p).first()
            process_paper(rec)
        else:
            n_queue += 1
            process_paper.queue(rec)

    print("Queued {} jobs".format(n_queue))
    return

if __name__ == "__main__":
    app.run(debug=True, threaded=True, use_reloader=False)
