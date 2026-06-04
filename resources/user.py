from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from passlib.hash import pbkdf2_sha256
from sqlalchemy.exc import IntegrityError

from db import db
from models import UserModel
from schemas import UserSchema, UserRegisterSchema, UserLoginSchema, UserUpdateSchema

blp = Blueprint("users", __name__, description="User registration, login and management")


@blp.route("/register")
class UserRegister(MethodView):

    @blp.arguments(UserRegisterSchema)
    @blp.response(201, UserSchema)
    def post(self, user_data):
        """Register a new user account."""
        # Read role from request — default to customer if not provided
        role = user_data.get("role", "customer")
        if role not in ["admin", "customer"]:
            role = "customer"

        user = UserModel(
            username=user_data["username"],
            email=user_data.get("email"),
            role=role,
            password_hash=pbkdf2_sha256.hash(user_data["password"]),
        )
        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            abort(409, message="A user with that username or email already exists.")
        return user


@blp.route("/login")
class UserLogin(MethodView):

    @blp.arguments(UserLoginSchema)
    def post(self, user_data):
        """Login and receive a JWT access token."""
        user = UserModel.query.filter_by(username=user_data["username"]).first()
        if user and pbkdf2_sha256.verify(user_data["password"], user.password_hash):
            token = create_access_token(identity=str(user.id), expires_delta=False)
            user.token = token
            db.session.commit()
            return {"access_token": token, "user": {"id": user.id, "username": user.username, "role": user.role}}, 200
        abort(401, message="Invalid username or password.")


@blp.route("/logout")
class UserLogout(MethodView):

    @jwt_required()
    def post(self):
        """Logout and clear stored token."""
        user = UserModel.query.get_or_404(int(get_jwt_identity()))
        user.token = None
        db.session.commit()
        return {"message": "Logged out successfully."}, 200


@blp.route("/users")
class UserList(MethodView):

    @jwt_required()
    @blp.response(200, UserSchema(many=True))
    def get(self):
        """List all users. Requires JWT."""
        return UserModel.query.all()


@blp.route("/users/<int:user_id>")
class User(MethodView):

    @jwt_required()
    @blp.response(200, UserSchema)
    def get(self, user_id):
        """Get user by ID. Requires JWT."""
        return UserModel.query.get_or_404(user_id)

    @jwt_required()
    @blp.arguments(UserUpdateSchema)
    @blp.response(200, UserSchema)
    def put(self, user_data, user_id):
        """Update user email. Requires JWT."""
        if int(get_jwt_identity()) != user_id:
            abort(403, message="You can only update your own account.")
        user = UserModel.query.get_or_404(user_id)
        user.email = user_data.get("email", user.email)
        db.session.commit()
        return user

    @jwt_required()
    def delete(self, user_id):
        """Delete user account. Requires JWT."""
        if int(get_jwt_identity()) != user_id:
            abort(403, message="You can only delete your own account.")
        user = UserModel.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return {"message": f"User '{user.username}' deleted."}, 200


@blp.route("/users/<int:user_id>/password")
class UserPassword(MethodView):

    @jwt_required()
    def patch(self, user_id):
        """Change password. Requires JWT + current password verification."""
        from flask import request
        if int(get_jwt_identity()) != user_id:
            abort(403, message="You can only change your own password.")
        data = request.get_json()
        current = data.get("current_password", "")
        new_pass = data.get("new_password", "")
        if not current or not new_pass:
            abort(400, message="Both current_password and new_password are required.")
        if len(new_pass) < 4:
            abort(400, message="New password must be at least 4 characters.")
        user = UserModel.query.get_or_404(user_id)
        if not pbkdf2_sha256.verify(current, user.password_hash):
            abort(401, message="Current password is incorrect.")
        user.password_hash = pbkdf2_sha256.hash(new_pass)
        db.session.commit()
        return {"message": "Password changed successfully."}, 200
