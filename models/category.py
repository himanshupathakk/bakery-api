from db import db


class CategoryModel(db.Model):
    __tablename__ = "categories"

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    # One category → many products (one-to-many)
    products = db.relationship("ProductModel", back_populates="category", lazy="dynamic")
