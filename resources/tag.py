from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError

from db import db
from models import TagModel
from schemas import TagSchema, PlainTagSchema
from utils import admin_required

blp = Blueprint("tags", __name__, description="Operations on tags")


@blp.route("/tags")
class TagList(MethodView):

    @blp.response(200, TagSchema(many=True))
    def get(self):
        """List all tags. Public."""
        return TagModel.query.all()

    @jwt_required()
    @blp.arguments(PlainTagSchema)
    @blp.response(201, TagSchema)
    def post(self, data):
        """Create a tag. Requires JWT + Admin role."""
        admin_required()
        tag = TagModel(**data)
        try:
            db.session.add(tag)
            db.session.commit()
        except IntegrityError:
            abort(400, message="A tag with that name already exists.")
        return tag


@blp.route("/tags/<int:tag_id>")
class Tag(MethodView):

    @blp.response(200, TagSchema)
    def get(self, tag_id):
        """Get a tag by ID. Public."""
        return TagModel.query.get_or_404(tag_id)

    @jwt_required()
    def delete(self, tag_id):
        """Delete a tag. Requires JWT + Admin role."""
        admin_required()
        tag = TagModel.query.get_or_404(tag_id)
        if tag.products:
            abort(400, message="Cannot delete tag still linked to products.")
        db.session.delete(tag)
        db.session.commit()
        return {"message": "Tag deleted."}, 200
