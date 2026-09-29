from decimal import Decimal
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory, session
from flask_migrate import Migrate
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config, INSTANCE_DIR
from models import Product, db
from routes.admin import admin_bp
from routes.shop import shop_bp
from utils.helpers import cart_count, format_currency
from utils.security import csrf_token, validate_csrf

migrate = Migrate()


def seed_products():
    if Product.query.count() > 0:
        return
    db.session.add_all(
        [
            Product(
                name="Full Chicken",
                description="A whole cleaned chicken, frozen fresh for family meals and Sunday roasts.",
                price=Decimal("8500.00"),
                unit="per bird",
                stock=24,
                image="full",
            ),
            Product(
                name="Chicken Laps",
                description="Tender chicken laps in a handy family-size pack, ready for soups, stews, and grills.",
                price=Decimal("6500.00"),
                unit="per 1.5kg bag",
                stock=18,
                image="laps",
            ),
            Product(
                name="Chicken Drumsticks",
                description="Juicy drumsticks portioned for easy cooking, with enough for a small gathering.",
                price=Decimal("5800.00"),
                unit="per 1.5kg bag",
                stock=20,
                image="drumsticks",
            ),
        ]
    )
    db.session.commit()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    Config.validate()
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    Path(INSTANCE_DIR).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    migrate.init_app(app, db)
    app.register_blueprint(shop_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_helpers():
        return {
            "format_currency": format_currency,
            "cart_count": cart_count(session.get("cart", {})),
            "csrf_token": csrf_token,
            "payment_bank": app.config["PAYMENT_BANK"],
            "payment_account_number": app.config["PAYMENT_ACCOUNT_NUMBER"],
            "payment_account_name": app.config["PAYMENT_ACCOUNT_NAME"],
        }

    @app.before_request
    def protect_state_changes():
        if app.config["IS_PRODUCTION"] and session.get("admin_logged_in"):
            session.permanent = True
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            validate_csrf()

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if app.config["IS_PRODUCTION"]:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; base-uri 'self'; form-action 'self'; "
            "img-src 'self' data:; style-src 'self' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; script-src 'self'",
        )
        if response.content_type and response.content_type.startswith("text/html"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.get("/health")
    def health():
        return jsonify(status="ok", service="beamers-farm")

    @app.get("/ready")
    def ready():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify(status="ready", service="beamers-farm")
        except SQLAlchemyError:
            db.session.rollback()
            return jsonify(status="not-ready", service="beamers-farm"), 503

    @app.get("/manus-routes.json")
    def route_manifest():
        return send_from_directory(app.static_folder, "manus-routes.json", mimetype="application/json")

    @app.errorhandler(400)
    def bad_request(error):
        return render_template("error.html", code=400, message=error.description or "Bad request."), 400

    @app.errorhandler(404)
    def not_found(error):
        return render_template("error.html", code=404, message="That page could not be found."), 404

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return render_template("error.html", code=500, message="Something went wrong on our side."), 500

    with app.app_context():
        if app.config["AUTO_CREATE_SCHEMA"]:
            db.create_all()
            seed_products()
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(__import__("os").environ.get("PORT", "3000")), debug=False)
