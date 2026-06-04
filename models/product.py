from db import db

# Many-to-many junction table: Products ↔ Tags
products_tags = db.Table(
    "products_tags",
    db.Column("product_id", db.Integer, db.ForeignKey("products.id"), primary_key=True),
    db.Column("tag_id",     db.Integer, db.ForeignKey("tags.id"),     primary_key=True),
)


class ProductModel(db.Model):
    __tablename__ = "products"

    id             = db.Column(db.Integer, primary_key=True)
    name           = db.Column(db.String(120), nullable=False)
    description    = db.Column(db.String(500), nullable=True)
    price          = db.Column(db.Float(precision=2), nullable=False)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    is_available   = db.Column(db.Boolean, nullable=False, default=True)
    image_url      = db.Column(db.String(500), nullable=True)

    # FK → category (one-to-many)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    category    = db.relationship("CategoryModel", back_populates="products")

    # Many-to-many → tags
    tags = db.relationship("TagModel", back_populates="products", secondary="products_tags")

    # One product → many order items
    order_items = db.relationship("OrderItemModel", back_populates="product")

    # One product → many reviews
    reviews = db.relationship("ReviewModel", back_populates="product", cascade="all, delete")
