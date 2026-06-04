from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError

from db import db
from models import ReviewModel, ProductModel
from schemas import ReviewSchema, PlainReviewSchema

blp = Blueprint("reviews", __name__, description="Product reviews")


@blp.route("/products/<int:product_id>/reviews")
class ProductReviews(MethodView):

    @blp.response(200, ReviewSchema(many=True))
    def get(self, product_id):
        """Get all reviews for a product. Public."""
        ProductModel.query.get_or_404(product_id)
        return ReviewModel.query.filter_by(product_id=product_id).all()

    @jwt_required()
    @blp.arguments(PlainReviewSchema)
    @blp.response(201, ReviewSchema)
    def post(self, data, product_id):
        """Add a review for a product. Requires JWT."""
        user_id = int(get_jwt_identity())
        ProductModel.query.get_or_404(product_id)
        existing = ReviewModel.query.filter_by(user_id=user_id, product_id=product_id).first()
        if existing:
            abort(400, message="You have already reviewed this product.")
        review = ReviewModel(user_id=user_id, product_id=product_id, **data)
        try:
            db.session.add(review)
            db.session.commit()
        except SQLAlchemyError:
            abort(500, message="Error saving review.")
        return review


@blp.route("/products/<int:product_id>/reviews/stats")
class ProductReviewStats(MethodView):

    def get(self, product_id):
        """Get review statistics for a product. Public.
        Returns average rating, total reviews, rating breakdown (1-5).
        """
        ProductModel.query.get_or_404(product_id)
        reviews = ReviewModel.query.filter_by(product_id=product_id).all()

        if not reviews:
            return {
                "product_id":    product_id,
                "total_reviews": 0,
                "average_rating": 0,
                "rating_breakdown": {"1":0, "2":0, "3":0, "4":0, "5":0}
            }, 200

        total    = len(reviews)
        avg      = round(sum(r.rating for r in reviews) / total, 2)
        breakdown = {"1":0, "2":0, "3":0, "4":0, "5":0}
        for r in reviews:
            breakdown[str(r.rating)] += 1

        return {
            "product_id":      product_id,
            "total_reviews":   total,
            "average_rating":  avg,
            "rating_breakdown": breakdown,
            "five_star_pct":   round((breakdown["5"] / total) * 100, 1)
        }, 200


@blp.route("/reviews/<int:review_id>")
class Review(MethodView):

    @jwt_required()
    def delete(self, review_id):
        """Delete a review. Only the reviewer can delete. Requires JWT."""
        user_id = int(get_jwt_identity())
        review  = ReviewModel.query.get_or_404(review_id)
        if review.user_id != user_id:
            abort(403, message="You can only delete your own reviews.")
        db.session.delete(review)
        db.session.commit()
        return {"message": "Review deleted."}, 200