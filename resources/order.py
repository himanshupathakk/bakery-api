from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError

from db import db
from models import OrderModel, OrderItemModel, ProductModel
from schemas import OrderSchema, CreateOrderSchema, OrderStatusSchema
from utils import admin_required

blp = Blueprint("orders", __name__, description="Order management")


@blp.route("/orders/stats")
class OrderStats(MethodView):

    @jwt_required()
    def get(self):
        """Get order statistics. Requires JWT + Admin role.
        Returns total orders, revenue, orders by status, top products.
        """
        admin_required()
        orders = OrderModel.query.all()

        # Count by status
        status_counts = {}
        for o in orders:
            status_counts[o.status] = status_counts.get(o.status, 0) + 1

        # Total revenue (exclude cancelled)
        total_revenue = sum(o.total_price for o in orders if o.status != "cancelled")

        # Top 5 products by quantity ordered
        from models import OrderItemModel
        from sqlalchemy import func
        top_products = db.session.query(
            OrderItemModel.product_id,
            func.sum(OrderItemModel.quantity).label("total_qty"),
            func.sum(OrderItemModel.price * OrderItemModel.quantity).label("total_revenue")
        ).group_by(OrderItemModel.product_id)\
         .order_by(func.sum(OrderItemModel.quantity).desc())\
         .limit(5).all()

        top_list = []
        for row in top_products:
            product = ProductModel.query.get(row.product_id)
            top_list.append({
                "product_id":   row.product_id,
                "product_name": product.name if product else "Deleted",
                "total_ordered": int(row.total_qty),
                "total_revenue": round(float(row.total_revenue), 2)
            })

        return {
            "total_orders":   len(orders),
            "total_revenue":  round(total_revenue, 2),
            "orders_by_status": status_counts,
            "top_products":   top_list,
            "average_order_value": round(total_revenue / len(orders), 2) if orders else 0
        }, 200


@blp.route("/orders")
class OrderList(MethodView):

    @jwt_required()
    @blp.response(200, OrderSchema(many=True))
    def get(self):
        """Get orders. Admin sees all, customer sees only their own."""
        from models import UserModel
        user_id = int(get_jwt_identity())
        user = UserModel.query.get(user_id)
        if user and user.role == "admin":
            return OrderModel.query.all()
        return OrderModel.query.filter_by(user_id=user_id).all()

    @jwt_required()
    @blp.arguments(CreateOrderSchema)
    @blp.response(201, OrderSchema)
    def post(self, data):
        """Place a new order. Requires JWT."""
        user_id = int(get_jwt_identity())
        if not data["items"]:
            abort(400, message="Order must contain at least one item.")

        total = 0.0
        order_items = []

        for entry in data["items"]:
            product = ProductModel.query.get(entry["product_id"])
            if not product:
                abort(404, message=f"Product {entry['product_id']} not found.")
            if not product.is_available:
                abort(400, message=f"'{product.name}' is not available.")
            qty = entry["quantity"]
            if product.stock_quantity < qty:
                abort(400, message=f"Not enough stock for '{product.name}'.")
            product.stock_quantity -= qty
            subtotal = product.price * qty
            total   += subtotal
            order_items.append(OrderItemModel(product_id=product.id, quantity=qty, price=product.price))

        order = OrderModel(user_id=user_id, total_price=round(total, 2), note=data.get("note"))
        try:
            db.session.add(order)
            db.session.flush()
            for oi in order_items:
                oi.order_id = order.id
                db.session.add(oi)
            db.session.commit()
        except SQLAlchemyError:
            abort(500, message="Error placing order.")
        return order


@blp.route("/orders/<int:order_id>")
class Order(MethodView):

    @jwt_required()
    @blp.response(200, OrderSchema)
    def get(self, order_id):
        """Get order by ID. Requires JWT."""
        user_id = int(get_jwt_identity())
        order   = OrderModel.query.get_or_404(order_id)
        from models import UserModel
        user = UserModel.query.get(user_id)
        if order.user_id != user_id and user.role != "admin":
            abort(403, message="You can only view your own orders.")
        return order

    @jwt_required()
    def delete(self, order_id):
        """Cancel a pending order (restores stock). Requires JWT."""
        user_id = int(get_jwt_identity())
        order   = OrderModel.query.get_or_404(order_id)
        if order.user_id != user_id:
            abort(403, message="You can only cancel your own orders.")
        if order.status != "pending":
            abort(400, message=f"Only pending orders can be cancelled. Current: '{order.status}'.")
        for oi in order.order_items:
            oi.product.stock_quantity += oi.quantity
        db.session.delete(order)
        db.session.commit()
        return {"message": "Order cancelled. Stock restored."}, 200


@blp.route("/orders/<int:order_id>/status")
class OrderStatus(MethodView):

    @jwt_required()
    @blp.arguments(OrderStatusSchema)
    @blp.response(200, OrderSchema)
    def patch(self, data, order_id):
        """Update order status. Requires JWT + Admin role."""
        admin_required()
        order        = OrderModel.query.get_or_404(order_id)
        order.status = data["status"]
        db.session.commit()
        return order


@blp.route("/users/<int:user_id>/orders")
class UserOrders(MethodView):

    @jwt_required()
    @blp.response(200, OrderSchema(many=True))
    def get(self, user_id):
        """Get all orders for a specific user. Requires JWT + Admin role."""
        admin_required()
        from models import UserModel
        UserModel.query.get_or_404(user_id)
        orders = OrderModel.query.filter_by(user_id=user_id).all()
        if not orders:
            abort(404, message=f"No orders found for user {user_id}.")
        return orders