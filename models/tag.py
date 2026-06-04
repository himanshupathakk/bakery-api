from db import db


class TagModel(db.Model):
    __tablename__ = "tags"

    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    # Many-to-many back-reference to products
    products = db.relationship("ProductModel", back_populates="tags", secondary="products_tags")
