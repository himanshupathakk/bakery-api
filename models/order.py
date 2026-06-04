from db import db
import datetime


class OrderModel(db.Model):
    __tablename__ = "orders"

    id          = db.Column(db.Integer, primary_key=True)
    status      = db.Column(db.String(20), nullable=False, default="pending")
    total_price = db.Column(db.Float(precision=2), nullable=False, default=0.0)
    note        = db.Column(db.String(255), nullable=True)
    created_at  = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

    # FK → user (one-to-many)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user    = db.relationship("UserModel", back_populates="orders")

    # One order → many order items (one-to-many)
    order_items = db.relationship("OrderItemModel", back_populates="order", cascade="all, delete", lazy="dynamic")


class OrderItemModel(db.Model):
    """
    Junction table: Order ↔ Product (many-to-many)
    Also stores quantity and price snapshot at time of order.
    """
    __tablename__ = "order_items"

    id       = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price    = db.Column(db.Float(precision=2), nullable=False)

    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    order    = db.relationship("OrderModel", back_populates="order_items")

    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    product    = db.relationship("ProductModel", back_populates="order_items")
