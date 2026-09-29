import json
import os
import ssl as ssl_module
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlencode, urlsplit, urlunsplit

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"


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
    DELIVERY_FEE = 1500
    PAYMENT_BANK = "Opay"
    PAYMENT_ACCOUNT_NUMBER = "8062074302"
    PAYMENT_ACCOUNT_NAME = "Dauda Akanni Bello"
    ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")
    # Development-only compatibility for the original demo password.
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "frostadmin")
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
            if cls.SQLALCHEMY_DATABASE_URI.startswith("sqlite:///"):
                raise RuntimeError("Production requires DATABASE_URL for durable shared storage.")
