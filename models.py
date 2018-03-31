from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Biorxiv(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String)
    user_id = db.Column(db.Integer)
    created = db.Column(db.DateTime)
    parse_status = db.Column(db.Integer)

class Test(Biorxiv):
    pass
