# models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Nomination(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    employee = db.Column(db.String(100), nullable=False)
    cookie_id = db.Column(db.String(128), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("category", "cookie_id", name="unique_vote_per_cookie"),
    )

    def __repr__(self):
        return f"<Nomination {self.employee} in {self.category}>"
    

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
