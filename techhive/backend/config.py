import os
from email.utils import parseaddr
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def load_environment(base_dir: Path = BASE_DIR) -> None:
    env_path = base_dir / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_environment()


def env_value(name: str, default=None, aliases: tuple[str, ...] = ()):
    for key in (name, *aliases):
        value = os.getenv(key)
        if value not in (None, ""):
            return value
    return default


def env_bool(name: str, default: str = "false", aliases: tuple[str, ...] = ()) -> bool:
    return str(env_value(name, default, aliases=aliases)).lower() == "true"


def env_int(name: str, default: str, aliases: tuple[str, ...] = ()) -> int:
    return int(str(env_value(name, default, aliases=aliases)))


def env_csv(name: str, default: str = "", aliases: tuple[str, ...] = ()) -> tuple[str, ...]:
    value = str(env_value(name, default, aliases=aliases) or "")
    items = [item.strip().lower() for item in value.split(",")]
    return tuple(item for item in items if item)


def resolve_sender_parts() -> tuple[str, str]:
    sender_value = env_value("SMTP_FROM_EMAIL", aliases=("MAIL_DEFAULT_SENDER",)) or "no-reply@techhive.local"
    parsed_name, parsed_email = parseaddr(sender_value)
    sender_email = parsed_email or sender_value
    sender_name = env_value("SMTP_FROM_NAME", aliases=("MAIL_DEFAULT_SENDER_NAME",)) or parsed_name or "TechHive"
    return sender_name, sender_email


SMTP_FROM_NAME_RESOLVED, SMTP_FROM_EMAIL_RESOLVED = resolve_sender_parts()


class Config:
    APP_NAME = "TechHive API"
    APP_VERSION = "0.1.0"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5000"))
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'techhive.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SWAGGER = {
        "title": "TechHive API",
        "uiversion": 3,
        "specs_route": "/docs/",
    }
    JSON_SORT_KEYS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "15")
    )
    JWT_REFRESH_TOKEN_EXPIRES_DAYS = int(
        os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", "7")
    )
    PASSWORD_RESET_TOKEN_EXPIRES_MINUTES = int(
        os.getenv("PASSWORD_RESET_TOKEN_EXPIRES_MINUTES", "30")
    )
    EMAIL_VERIFICATION_TOKEN_EXPIRES_HOURS = int(
        os.getenv("EMAIL_VERIFICATION_TOKEN_EXPIRES_HOURS", "24")
    )
    PAYMENT_CALLBACK_BASE_URL = os.getenv(
        "PAYMENT_CALLBACK_BASE_URL",
        "http://localhost:5000/api/v1/payments/webhooks",
    )
    MPESA_BASE_URL = os.getenv("MPESA_BASE_URL", "https://sandbox.safaricom.co.ke")
    MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
    MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
    MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE")
    MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
    MPESA_TRANSACTION_TYPE = os.getenv(
        "MPESA_TRANSACTION_TYPE",
        "CustomerPayBillOnline",
    )
    MPESA_ACCOUNT_REFERENCE = os.getenv("MPESA_ACCOUNT_REFERENCE", "TechHive")
    MPESA_TRANSACTION_DESC = os.getenv("MPESA_TRANSACTION_DESC", "TechHive payment")
    PAYMENT_ENABLED_METHODS = env_csv(
        "PAYMENT_ENABLED_METHODS",
        "mpesa,manual,cash_on_delivery,stripe,flutterwave,paypal",
    )
    PAYMENT_PRIMARY_METHOD = str(os.getenv("PAYMENT_PRIMARY_METHOD", "mpesa")).strip().lower()
    MPESA_ALLOW_UNSIGNED_CALLBACKS = (
        os.getenv("MPESA_ALLOW_UNSIGNED_CALLBACKS", "true").lower() == "true"
    )
    MPESA_RECONCILIATION_TIMEOUT_MINUTES = int(
        os.getenv("MPESA_RECONCILIATION_TIMEOUT_MINUTES", "15")
    )
    MPESA_RECONCILIATION_RETRY_DELAY_MINUTES = int(
        os.getenv("MPESA_RECONCILIATION_RETRY_DELAY_MINUTES", "5")
    )
    MPESA_RECONCILIATION_MAX_ATTEMPTS = int(
        os.getenv("MPESA_RECONCILIATION_MAX_ATTEMPTS", "2")
    )
    MPESA_RECONCILIATION_BATCH_LIMIT = int(
        os.getenv("MPESA_RECONCILIATION_BATCH_LIMIT", "100")
    )
    MPESA_RECONCILIATION_SCHEDULE_MINUTES = int(
        os.getenv("MPESA_RECONCILIATION_SCHEDULE_MINUTES", "5")
    )
    PAYMENTS_ALLOW_SIMULATION = os.getenv("PAYMENTS_ALLOW_SIMULATION", "true").lower() == "true"
    MPESA_WEBHOOK_SECRET = os.getenv("MPESA_WEBHOOK_SECRET", "mpesa-dev-secret")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "stripe-dev-secret")
    FLUTTERWAVE_WEBHOOK_SECRET = os.getenv(
        "FLUTTERWAVE_WEBHOOK_SECRET",
        "flutterwave-dev-secret",
    )
    PAYPAL_WEBHOOK_SECRET = os.getenv("PAYPAL_WEBHOOK_SECRET", "paypal-dev-secret")
    TESTING = False
    DEBUG = False
    GUNICORN_TIMEOUT = int(os.getenv("GUNICORN_TIMEOUT", "60"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "*")
    RATE_LIMIT_AUTH_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_AUTH_MAX_REQUESTS", "5"))
    RATE_LIMIT_AUTH_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_AUTH_WINDOW_SECONDS", "60"))
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", "development")
    SENTRY_TRACES_SAMPLE_RATE = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0"))
    GUNICORN_WORKERS = int(os.getenv("GUNICORN_WORKERS", "2"))
    TASK_QUEUE_ENABLED = os.getenv("TASK_QUEUE_ENABLED", "false").lower() == "true"
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")
    CELERY_TASK_ALWAYS_EAGER = (
        os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"
    )
    SMTP_HOST = env_value("SMTP_HOST", aliases=("MAIL_SERVER",))
    SMTP_PORT = env_int("SMTP_PORT", "587", aliases=("MAIL_PORT",))
    SMTP_USERNAME = env_value("SMTP_USERNAME", aliases=("MAIL_USERNAME",))
    SMTP_PASSWORD = env_value("SMTP_PASSWORD", aliases=("MAIL_PASSWORD",))
    SMTP_USE_TLS = env_bool("SMTP_USE_TLS", "true", aliases=("MAIL_USE_TLS",))
    SMTP_USE_SSL = env_bool("SMTP_USE_SSL", "false", aliases=("MAIL_USE_SSL",))
    SMTP_TIMEOUT_SECONDS = env_int("SMTP_TIMEOUT_SECONDS", "20", aliases=("MAIL_TIMEOUT_SECONDS",))
    SMTP_FROM_EMAIL = SMTP_FROM_EMAIL_RESOLVED
    SMTP_FROM_NAME = SMTP_FROM_NAME_RESOLVED
    SMTP_REPLY_TO = env_value("SMTP_REPLY_TO", aliases=("MAIL_REPLY_TO",))
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_FROM_NUMBER = env_value("TWILIO_FROM_NUMBER", aliases=("TWILIO_PHONE_NUMBER",))
    TWILIO_MESSAGING_SERVICE_SID = os.getenv("TWILIO_MESSAGING_SERVICE_SID")
    TWILIO_API_BASE_URL = os.getenv("TWILIO_API_BASE_URL", "https://api.twilio.com")
    BULK_NOTIFICATION_BATCH_SIZE = int(os.getenv("BULK_NOTIFICATION_BATCH_SIZE", "250"))
    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")
    STORAGE_LOCAL_ROOT = os.getenv("STORAGE_LOCAL_ROOT", str(BASE_DIR / "media"))
    STORAGE_PUBLIC_BASE_URL = os.getenv("STORAGE_PUBLIC_BASE_URL", "/media")
    STORAGE_MAX_UPLOAD_BYTES = int(os.getenv("STORAGE_MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))
    MPESA_LOG_DIR = os.getenv("MPESA_LOG_DIR", str(BASE_DIR / "logs"))
    MPESA_LOG_FILE = os.getenv("MPESA_LOG_FILE", "mpesa.log")
    MPESA_LOG_MAX_BYTES = int(os.getenv("MPESA_LOG_MAX_BYTES", "1000000"))
    MPESA_LOG_BACKUP_COUNT = int(os.getenv("MPESA_LOG_BACKUP_COUNT", "5"))


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    PAYMENT_ENABLED_METHODS = ("mpesa", "manual", "cash_on_delivery", "stripe", "flutterwave", "paypal")
    PAYMENTS_ALLOW_SIMULATION = True
    MPESA_CONSUMER_KEY = None
    MPESA_CONSUMER_SECRET = None
    MPESA_SHORTCODE = None
    MPESA_PASSKEY = None
    SMTP_HOST = None
    SMTP_USERNAME = None
    SMTP_PASSWORD = None
    TWILIO_ACCOUNT_SID = None
    TWILIO_AUTH_TOKEN = None
    TWILIO_FROM_NUMBER = None
    TWILIO_MESSAGING_SERVICE_SID = None
    STORAGE_LOCAL_ROOT = str(BASE_DIR / ".test_media")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    PAYMENTS_ALLOW_SIMULATION = False
    MPESA_ALLOW_UNSIGNED_CALLBACKS = False


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(config_name: str | None = None) -> type[Config]:
    selected = config_name or os.getenv("FLASK_ENV", "development")
    return config_by_name.get(selected, DevelopmentConfig)
