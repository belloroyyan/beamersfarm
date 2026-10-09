import json
import os
import ssl as ssl_module
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlencode, urlsplit, urlunsplit

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"


def normalize_vapid_private_key(value):
    key = (value or "").strip()
    if key.startswith("-----BEGIN "):
        key = (
            key.replace("\\r\\n", "\n")
            .replace("\\n", "\n")
            .replace("\\r", "\n")
            .replace("\r\n", "\n")
            .replace("\r", "\n")
        )
    return key


def validate_vapid_private_key(value):
    try:
        if value.startswith("-----BEGIN "):
            pem = value.encode("utf-8")
        else:
            path = Path(value)
            if not path.is_file():
                raise ValueError("not a PEM value or existing file")
            pem = path.read_bytes()

        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec

        private_key = serialization.load_pem_private_key(pem, password=None)
        if not isinstance(private_key, ec.EllipticCurvePrivateKey) or not isinstance(
            private_key.curve, ec.SECP256R1
        ):
            raise ValueError("VAPID requires an unencrypted P-256 EC private key")
    except Exception as exc:
        raise RuntimeError(
            "VAPID_PRIVATE_KEY must be valid unencrypted P-256 PEM text or a path to a PEM file."
        ) from exc


def database_config():
    # Managed Webdev supplies DATABASE_URL. CHICKEN_DATABASE_URL remains a
    # convenient explicit override for local development and tests.
    url = os.environ.get("CHICKEN_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        url = f"sqlite:///{INSTANCE_DIR / 'database.db'}"
    connect_args = {}
    if url.startswith("mysql://"):
        url = url.replace("mysql://", "mysql+pymysql://", 1)
    if url.startswith("mysql+pymysql://"):
        parts = urlsplit(url)
        query = parse_qs(parts.query, keep_blank_values=True)
        raw_ssl = query.pop("ssl", [None])[0]
        if raw_ssl:
            options = json.loads(unquote(raw_ssl))
            if options.get("rejectUnauthorized", True):
                ca_file = ssl_module.get_default_verify_paths().cafile
                ssl_options = {"check_hostname": True, "verify_mode": "required"}
                if ca_file:
                    ssl_options["ca"] = ca_file
            else:
                ssl_options = {"check_hostname": False, "verify_mode": "none"}
            connect_args["ssl"] = ssl_options
            url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), parts.fragment))
    return url, connect_args


DATABASE_URI, DATABASE_CONNECT_ARGS = database_config()


class Config:
    ENVIRONMENT = os.environ.get("APP_ENV", "development").lower()
    IS_PRODUCTION = ENVIRONMENT == "production"
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-frost-and-fowl-key")
    SQLALCHEMY_DATABASE_URI = DATABASE_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "connect_args": DATABASE_CONNECT_ARGS}
    PRODUCT_UPLOAD_FOLDER = str(BASE_DIR / "static" / "uploads" / "products")
    UPDATE_UPLOAD_FOLDER = str(BASE_DIR / "static" / "uploads" / "updates")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
    DELIVERY_FEE = 1500
    SHOP_OPEN_DEFAULT = os.environ.get("SHOP_OPEN_DEFAULT", "true").lower() == "true"
    SHOP_CLOSED_MESSAGE = os.environ.get(
        "SHOP_CLOSED_MESSAGE",
        "We are currently closed for orders. You can still browse our products.",
    )
    PAYMENT_BANK = os.environ.get("PAYMENT_BANK", "Opay")
    PAYMENT_ACCOUNT_NUMBER = os.environ.get("PAYMENT_ACCOUNT_NUMBER", "8062074302")
    PAYMENT_ACCOUNT_NAME = os.environ.get("PAYMENT_ACCOUNT_NAME", "Dauda Akanni Bello")
    PAYSTACK_ENABLED = os.environ.get("PAYSTACK_ENABLED", "false").lower() == "true"
    PAYSTACK_PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY", "").strip()
    PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY", "").strip()
    MESSAGING_ENABLED = os.environ.get("MESSAGING_ENABLED", "false").lower() == "true"
    MESSAGING_MODE = os.environ.get("MESSAGING_MODE", "mock").lower()
    WHATSAPP_ENABLED = os.environ.get("WHATSAPP_ENABLED", "false").lower() == "true"
    WHATSAPP_GRAPH_API_VERSION = os.environ.get("WHATSAPP_GRAPH_API_VERSION", "v26.0")
    WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
    WHATSAPP_BUSINESS_ACCOUNT_ID = os.environ.get("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
    WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
    WHATSAPP_TEMPLATE_NAME = os.environ.get("WHATSAPP_TEMPLATE_NAME", "beamers_order_confirmed")
    WHATSAPP_TEMPLATE_LANGUAGE = os.environ.get("WHATSAPP_TEMPLATE_LANGUAGE", "en")
    WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")
    META_APP_SECRET = os.environ.get("META_APP_SECRET", "")
    WHATSAPP_MAX_ATTEMPTS = int(os.environ.get("WHATSAPP_MAX_ATTEMPTS", "5"))
    ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")
    # Development-only compatibility for the original demo password.
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "frostadmin")
    DISPATCH_RIDER_PASSWORD_HASH = os.environ.get("DISPATCH_RIDER_PASSWORD_HASH", "")
    # Development-only convenience; production must use a password hash.
    DISPATCH_RIDER_PASSWORD = os.environ.get("DISPATCH_RIDER_PASSWORD", "frostdispatch")
    VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "").strip()
    # Accept protected PEM text (including literal \\n sequences) or a mounted PEM file path.
    VAPID_PRIVATE_KEY = normalize_vapid_private_key(os.environ.get("VAPID_PRIVATE_KEY", ""))
    VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT", "").strip()
    AUTO_CREATE_SCHEMA = os.environ.get(
        "AUTO_CREATE_SCHEMA", "false" if IS_PRODUCTION else "true"
    ).lower() == "true"
    SESSION_COOKIE_NAME = "frost_fowl_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = IS_PRODUCTION
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024

    @classmethod
    def validate(cls):
        if cls.IS_PRODUCTION:
            if not cls.SECRET_KEY or cls.SECRET_KEY.startswith("dev-only-"):
                raise RuntimeError("SECRET_KEY must be set to a strong value in production.")
            if not cls.ADMIN_PASSWORD_HASH:
                raise RuntimeError("ADMIN_PASSWORD_HASH must be set in production.")
            if not cls.DISPATCH_RIDER_PASSWORD_HASH:
                raise RuntimeError("DISPATCH_RIDER_PASSWORD_HASH must be set in production.")
            if cls.SQLALCHEMY_DATABASE_URI.startswith("sqlite:///" ):
                raise RuntimeError("Production requires DATABASE_URL for durable shared storage.")
            vapid_settings = (cls.VAPID_PUBLIC_KEY, cls.VAPID_PRIVATE_KEY, cls.VAPID_SUBJECT)
            if any(vapid_settings) and not all(vapid_settings):
                raise RuntimeError(
                    "Dispatch push notifications require VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, and VAPID_SUBJECT together."
                )
            if cls.VAPID_SUBJECT and not cls.VAPID_SUBJECT.startswith(("mailto:", "https://")):
                raise RuntimeError("VAPID_SUBJECT must be a mailto: or https:// contact URL.")
            if all(vapid_settings):
                validate_vapid_private_key(cls.VAPID_PRIVATE_KEY)
            if cls.WHATSAPP_ENABLED:
                required = {
                    "WHATSAPP_PHONE_NUMBER_ID": cls.WHATSAPP_PHONE_NUMBER_ID,
                    "WHATSAPP_ACCESS_TOKEN": cls.WHATSAPP_ACCESS_TOKEN,
                    "WHATSAPP_VERIFY_TOKEN": cls.WHATSAPP_VERIFY_TOKEN,
                    "META_APP_SECRET": cls.META_APP_SECRET,
                }
                missing = [name for name, value in required.items() if not value]
                if missing:
                    raise RuntimeError("WhatsApp is enabled but required variables are missing: " + ", ".join(missing))
            if cls.PAYSTACK_ENABLED:
                missing = [
                    name for name, value in {
                        "PAYSTACK_PUBLIC_KEY": cls.PAYSTACK_PUBLIC_KEY,
                        "PAYSTACK_SECRET_KEY": cls.PAYSTACK_SECRET_KEY,
                    }.items() if not value
                ]
                if missing:
                    raise RuntimeError("Paystack is enabled but required variables are missing: " + ", ".join(missing))
