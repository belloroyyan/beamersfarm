from decimal import Decimal
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory, session
from flask_migrate import Migrate
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config, INSTANCE_DIR
from models import DeliveryZone, Product, ShopSettings, db
from routes.admin import admin_bp
from routes.shop import shop_bp
from routes.whatsapp import whatsapp_bp
from routes.complaints import complaints_bp
from routes.dispatch import dispatch_bp
from routes.salesperson import salesperson_bp
from routes.payments import payments_bp
from routes.reviews import reviews_bp
from utils.helpers import cart_count, format_currency, format_quantity
from utils.greetings import time_of_day_greeting
from utils.updates import linkify, update_image_url
from utils.partner_ads import partner_image_url
from utils.gallery import gallery_image_url
from utils.product_images import product_image_url
from utils.security import csrf_token, validate_csrf

migrate = Migrate()


def seed_products():
    if Product.query.count() > 0:
        return
    db.session.add_all(
        [
            Product(
                name="Full Chicken",
                description="A whole cleaned chicken, frozen fresh for family meals and Sunday roasts. Sold per bird at the listed price.",
                price=Decimal("8500.00"),
                unit="bird",
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


def ensure_shop_settings():
    if not ShopSettings.query.get(1):
        db.session.add(
            ShopSettings(
                id=1,
                is_open=Config.SHOP_OPEN_DEFAULT,
                closed_message=Config.SHOP_CLOSED_MESSAGE,
            )
        )
        db.session.commit()


def ensure_delivery_zones():
    if DeliveryZone.query.count() > 0:
        return
    db.session.add_all(
        [
            DeliveryZone(
                name="Osogbo — Standard delivery",
                description="Standard Osogbo delivery tier. Please confirm with us if you are unsure whether your neighborhood is included.",
                fee=Decimal("1500.00"),
                sort_order=10,
            ),
            DeliveryZone(
                name="Farm pickup (Elapop Estate)",
                description="Collect your order from Beamers Farm; no delivery fee.",
                fee=Decimal("0.00"),
                is_pickup=True,
                sort_order=0,
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
    app.register_blueprint(whatsapp_bp)
    app.register_blueprint(complaints_bp)
    app.register_blueprint(dispatch_bp)
    app.register_blueprint(salesperson_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(reviews_bp)

    app.jinja_env.filters["linkify"] = linkify

    @app.context_processor
    def inject_helpers():
        shop_settings = ShopSettings.query.get(1)
        return {
            "greeting": time_of_day_greeting(),
            "product_image_url": product_image_url,
            "update_image_url": update_image_url,
            "partner_image_url": partner_image_url,
            "gallery_image_url": gallery_image_url,
            "format_currency": format_currency,
            "format_quantity": format_quantity,
            "cart_count": cart_count(session.get("cart", {})),
            "csrf_token": csrf_token,
            "payment_bank": app.config["PAYMENT_BANK"],
            "payment_account_number": app.config["PAYMENT_ACCOUNT_NUMBER"],
            "payment_account_name": app.config["PAYMENT_ACCOUNT_NAME"],
            "paystack_enabled": app.config["PAYSTACK_ENABLED"],
            "paystack_public_key": app.config["PAYSTACK_PUBLIC_KEY"],
            "shop_is_open": shop_settings.is_open if shop_settings else app.config["SHOP_OPEN_DEFAULT"],
            "shop_closed_message": shop_settings.closed_message if shop_settings else app.config["SHOP_CLOSED_MESSAGE"],
        }

    @app.before_request
    def protect_state_changes():
        if app.config["IS_PRODUCTION"] and (session.get("staff_role") or session.get("admin_logged_in")):
            session.permanent = True
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.blueprint not in {"whatsapp", "payments"}:
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

    @app.get("/manifest.webmanifest")
    def pwa_manifest():
        response = send_from_directory(
            app.static_folder, "manifest.webmanifest", mimetype="application/manifest+json"
        )
        response.headers["Cache-Control"] = "public, max-age=3600"
        return response

    @app.get("/service-worker.js")
    def pwa_service_worker():
        response = send_from_directory(
            app.static_folder, "service-worker.js", mimetype="application/javascript"
        )
        response.headers["Service-Worker-Allowed"] = "/"
        response.headers["Cache-Control"] = "no-cache"
        return response

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
            ensure_shop_settings()
            ensure_delivery_zones()
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(__import__("os").environ.get("PORT", "3000")), debug=False)
