from db import db


class UserModel(db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=True)
    role          = db.Column(db.String(20), nullable=False, default="customer")  # admin / customer
    password_hash = db.Column(db.String(256), nullable=False)
    token         = db.Column(db.String(512), nullable=True)

    # One user → many orders
    orders = db.relationship("OrderModel", back_populates="user", lazy="dynamic", cascade="all, delete")
    # One user → many reviews
    reviews = db.relationship("ReviewModel", back_populates="user", lazy="dynamic", cascade="all, delete")
