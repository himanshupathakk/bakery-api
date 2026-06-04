from db import db
import datetime


class ReviewModel(db.Model):
    __tablename__ = "reviews"

    id         = db.Column(db.Integer, primary_key=True)
    rating     = db.Column(db.Integer, nullable=False)   # 1-5
    comment    = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

    # FK → user
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user    = db.relationship("UserModel", back_populates="reviews")

    # FK → product
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    product    = db.relationship("ProductModel", back_populates="reviews")
