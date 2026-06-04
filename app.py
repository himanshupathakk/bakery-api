import os
import signal
import atexit
from flask import Flask, send_from_directory
from flask_smorest import Api
from flask_jwt_extended import JWTManager

from db import db
import models

from resources.user     import blp as UserBlueprint
from resources.category import blp as CategoryBlueprint
from resources.product  import blp as ProductBlueprint
from resources.tag      import blp as TagBlueprint
from resources.order    import blp as OrderBlueprint
from resources.review   import blp as ReviewBlueprint

#Clear all JWT tokens on server shutdown
def clear_all_tokens(app):
    with app.app_context():
        try:
            from models.user import UserModel
            count = db.session.query(UserModel).filter(UserModel.token != None).count()
            db.session.query(UserModel).update({"token": None})
            db.session.commit()
            print(f"\n✅ Shutdown — cleared {count} active token(s).")
        except Exception as e:
            print(f"\n⚠️ Could not clear tokens: {e}")


def create_app(db_url=None):
    app = Flask(__name__)

    # ── Configuration ─────────────────────────────────────────────────────────
    app.config["PROPAGATE_EXCEPTIONS"]    = True
    app.config["API_TITLE"]               = "Sweet Crumbs Bakery API"
    app.config["API_VERSION"]             = "v1"
    app.config["OPENAPI_VERSION"]         = "3.0.3"
    app.config["OPENAPI_URL_PREFIX"]      = "/"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = "/swagger-ui"
    app.config["OPENAPI_SWAGGER_UI_URL"]  = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    app.config["SQLALCHEMY_DATABASE_URI"]        = db_url or os.getenv("DATABASE_URL", "sqlite:///bakery.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["JWT_SECRET_KEY"]           = os.getenv("JWT_SECRET_KEY", "bakery-secret-key-change-in-prod")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)
    JWTManager(app)
    api = Api(app)

    # ── Tables ────────────────────────────────────────────────────────────────
    with app.app_context():
        db.create_all()

    # ── Blueprints ────────────────────────────────────────────────────────────
    api.register_blueprint(UserBlueprint)
    api.register_blueprint(CategoryBlueprint)
    api.register_blueprint(ProductBlueprint)
    api.register_blueprint(TagBlueprint)
    api.register_blueprint(OrderBlueprint)
    api.register_blueprint(ReviewBlueprint)

    # ── UI Routes ─────────────────────────────────────────────────────────────
    @app.route("/")
    @app.route("/shop")
    def shop():
        return send_from_directory("static", "shop.html")

    @app.route("/upload", methods=["POST"])
    def upload_image():
        import os, uuid
        from flask import request, jsonify
        from flask_jwt_extended import verify_jwt_in_request
        try:
            verify_jwt_in_request()
        except Exception:
            return jsonify({"message": "JWT required"}), 401
        if "image" not in request.files:
            return jsonify({"message": "No image provided"}), 400
        file = request.files["image"]
        if file.filename == "":
            return jsonify({"message": "No file selected"}), 400
        ext = file.filename.rsplit(".", 1)[-1].lower()
        if ext not in {"png","jpg","jpeg","gif","webp"}:
            return jsonify({"message": "Only image files allowed"}), 400
        filename = f"{uuid.uuid4().hex}.{ext}"
        upload_folder = os.path.join(app.static_folder, "uploads")
        os.makedirs(upload_folder, exist_ok=True)
        file.save(os.path.join(upload_folder, filename))
        return jsonify({"image_url": f"/static/uploads/{filename}"}), 200

    @app.route("/static/defaults/<filename>")
    def default_image(filename):
        import os
        return send_from_directory(os.path.join(app.static_folder, "defaults"), filename)

    @app.route("/static/uploads/<filename>")
    def uploaded_file(filename):
        import os
        return send_from_directory(os.path.join(app.static_folder, "uploads"), filename)


    @app.route("/admin")
    def admin():
        return send_from_directory("static", "admin.html")

    # ── Shutdown ──────────────────────────────────────────────────────────────
    atexit.register(clear_all_tokens, app)

    def handle_shutdown(signum, frame):
        clear_all_tokens(app)
        raise SystemExit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=False, host="0.0.0.0", port=5000)
