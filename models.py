from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.hybrid import hybrid_property

db = SQLAlchemy()

class Biorxiv(db.Model):
    id              = db.Column(db.String, primary_key=True)
    created         = db.Column(db.DateTime)
    title           = db.Column(db.String)
    parse_status    = db.Column(db.Integer)
    parse_data      = db.Column(db.String)
    author_contact  = db.Column(db.String)
    email_sent      = db.Column(db.Integer)

class Test(Biorxiv):
    pass
