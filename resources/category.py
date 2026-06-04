from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError

from db import db
from models import CategoryModel
from schemas import CategorySchema, PlainCategorySchema
from utils import admin_required

blp = Blueprint("categories", __name__, description="Operations on product categories")


@blp.route("/categories")
class CategoryList(MethodView):

    @blp.response(200, CategorySchema(many=True))
    def get(self):
        """List all categories. Public."""
        return CategoryModel.query.all()

    @jwt_required()
    @blp.arguments(PlainCategorySchema)
    @blp.response(201, CategorySchema)
    def post(self, data):
        """Create a category. Requires JWT + Admin."""
        admin_required()
        cat = CategoryModel(**data)
        try:
            db.session.add(cat)
            db.session.commit()
        except IntegrityError:
            abort(400, message="A category with that name already exists.")
        return cat


@blp.route("/categories/<int:category_id>")
class Category(MethodView):

    @blp.response(200, CategorySchema)
    def get(self, category_id):
        """Get category by ID. Public."""
        return CategoryModel.query.get_or_404(category_id)

    @jwt_required()
    @blp.arguments(PlainCategorySchema)
    @blp.response(200, CategorySchema)
    def put(self, data, category_id):
        """Fully update a category. Requires JWT + Admin."""
        admin_required()
        cat = CategoryModel.query.get_or_404(category_id)
        cat.name        = data.get("name", cat.name)
        cat.description = data.get("description", cat.description)
        try:
            db.session.commit()
        except IntegrityError:
            abort(400, message="A category with that name already exists.")
        return cat

    @jwt_required()
    @blp.arguments(PlainCategorySchema(partial=True))
    @blp.response(200, CategorySchema)
    def patch(self, data, category_id):
        """Partially update a category. Requires JWT + Admin.
        Send only the fields you want to change.
        Example: just send { "description": "New description" }
        """
        admin_required()
        cat = CategoryModel.query.get_or_404(category_id)
        if "name" in data and data["name"]:
            cat.name = data["name"]
        if "description" in data:
            cat.description = data["description"]
        try:
            db.session.commit()
        except IntegrityError:
            abort(400, message="A category with that name already exists.")
        return cat

    @jwt_required()
    def delete(self, category_id):
        """Delete a category. Requires JWT + Admin."""
        admin_required()
        cat = CategoryModel.query.get_or_404(category_id)
        db.session.delete(cat)
        db.session.commit()
        return {"message": "Category deleted."}, 200