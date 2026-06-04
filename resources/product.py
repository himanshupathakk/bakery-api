from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import SQLAlchemyError

from db import db
from models import ProductModel
from schemas import ProductSchema, ProductUpdateSchema
from utils import admin_required

blp = Blueprint("products", __name__, description="Operations on bakery products")


@blp.route("/products/search")
class ProductSearch(MethodView):

    @blp.response(200, ProductSchema(many=True))
    def get(self):
        """Search products by name, category, min/max price. Public.
        Query params: q, category_id, min_price, max_price, available
        Example: /products/search?q=chocolate&min_price=5&max_price=50
        """
        from flask import request
        q            = request.args.get("q", "").strip()
        category_id  = request.args.get("category_id", type=int)
        min_price    = request.args.get("min_price", type=float)
        max_price    = request.args.get("max_price", type=float)
        available    = request.args.get("available", "").lower()

        query = ProductModel.query

        if q:
            query = query.filter(ProductModel.name.ilike(f"%{q}%"))
        if category_id:
            query = query.filter_by(category_id=category_id)
        if min_price is not None:
            query = query.filter(ProductModel.price >= min_price)
        if max_price is not None:
            query = query.filter(ProductModel.price <= max_price)
        if available == "true":
            query = query.filter_by(is_available=True)
        elif available == "false":
            query = query.filter_by(is_available=False)

        results = query.all()
        if not results:
            abort(404, message="No products found matching your search.")
        return results


@blp.route("/products/featured")
class ProductFeatured(MethodView):

    @blp.response(200, ProductSchema(many=True))
    def get(self):
        """Get featured (bestseller) products that are available. Public."""
        from models import TagModel
        tag = TagModel.query.filter_by(name="bestseller").first()
        if not tag:
            abort(404, message="No featured products found.")
        featured = [p for p in tag.products if p.is_available and p.stock_quantity > 0]
        if not featured:
            abort(404, message="No featured products available right now.")
        return featured


@blp.route("/products")
class ProductList(MethodView):

    @blp.response(200, ProductSchema(many=True))
    def get(self):
        """List all products. Public."""
        return ProductModel.query.all()

    @jwt_required()
    @blp.arguments(ProductSchema)
    @blp.response(201, ProductSchema)
    def post(self, data):
        """Create a product. Requires JWT + Admin role."""
        admin_required()
        product = ProductModel(**data)
        try:
            db.session.add(product)
            db.session.commit()
        except SQLAlchemyError:
            abort(500, message="An error occurred while creating the product.")
        return product


@blp.route("/products/<int:product_id>")
class Product(MethodView):

    @blp.response(200, ProductSchema)
    def get(self, product_id):
        """Get a product by ID. Public."""
        return ProductModel.query.get_or_404(product_id)

    @jwt_required()
    @blp.arguments(ProductUpdateSchema)
    @blp.response(200, ProductSchema)
    def put(self, data, product_id):
        """Fully update a product. Requires JWT + Admin role."""
        admin_required()
        product = ProductModel.query.get_or_404(product_id)
        for key, val in data.items():
            setattr(product, key, val)
        if "image_url" in data and data["image_url"] is None:
            product.image_url = None
        db.session.commit()
        return product

    @jwt_required()
    @blp.arguments(ProductUpdateSchema)
    @blp.response(200, ProductSchema)
    def patch(self, data, product_id):
        """Partially update a product (only fields provided). Requires JWT + Admin role.
        Example: just send { "price": 29.99 } to update only the price.
        """
        admin_required()
        product = ProductModel.query.get_or_404(product_id)
        # Only update fields that were actually sent
        for key, val in data.items():
            if val is not None:
                setattr(product, key, val)
        db.session.commit()
        return product

    @jwt_required()
    def delete(self, product_id):
        """Delete a product. Requires JWT + Admin role."""
        admin_required()
        product = ProductModel.query.get_or_404(product_id)
        db.session.delete(product)
        db.session.commit()
        return {"message": "Product deleted."}, 200


@blp.route("/products/<int:product_id>/tags/<int:tag_id>")
class ProductTagLink(MethodView):

    @jwt_required()
    @blp.response(201, ProductSchema)
    def post(self, product_id, tag_id):
        """Link a tag to a product (many-to-many). Requires JWT + Admin."""
        admin_required()
        from models import TagModel
        product = ProductModel.query.get_or_404(product_id)
        tag     = TagModel.query.get_or_404(tag_id)
        if tag in product.tags:
            abort(400, message="Tag already linked to this product.")
        product.tags.append(tag)
        db.session.commit()
        return product

    @jwt_required()
    @blp.response(200, ProductSchema)
    def delete(self, product_id, tag_id):
        """Unlink a tag from a product. Requires JWT + Admin."""
        admin_required()
        from models import TagModel
        product = ProductModel.query.get_or_404(product_id)
        tag     = TagModel.query.get_or_404(tag_id)
        if tag not in product.tags:
            abort(400, message="Tag is not linked to this product.")
        product.tags.remove(tag)
        db.session.commit()
        return product


@blp.route("/products/<int:product_id>/tags")
class ProductTags(MethodView):

    @blp.response(200, ProductSchema)
    def get(self, product_id):
        """Get all tags for a product. Public."""
        return ProductModel.query.get_or_404(product_id)


@blp.route("/categories/<int:category_id>/products")
class CategoryProducts(MethodView):

    @blp.response(200, ProductSchema(many=True))
    def get(self, category_id):
        """Get all products in a category. Public."""
        return ProductModel.query.filter_by(category_id=category_id).all()