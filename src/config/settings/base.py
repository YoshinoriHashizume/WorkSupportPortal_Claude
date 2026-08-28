from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # src/
REPO_ROOT = BASE_DIR.parent  # docker env root


def load_dotenv(path: Path, *, override: bool = False) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8-sig")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if override:
            os.environ[key] = value
        else:
            os.environ.setdefault(key, value)


def is_production_settings_module(settings_module: str | None = None) -> bool:
    module = settings_module if settings_module is not None else os.environ.get("DJANGO_SETTINGS_MODULE", "")
    name = module.rsplit(".", 1)[-1]
    return name == "production"


def load_repo_env_files() -> None:
    """リポジトリルートの env ファイルを読み込む。

    - `config.settings.production`: `.env.production` を優先（override）
    - 開発（Docker Compose / DevContainer 含む）: `.env.local` / `.env` のみ。
      `.env.production` は読まない（開発用 DB パスワード等を上書きしないため）。
    """
    if is_production_settings_module():
        load_dotenv(REPO_ROOT / ".env.production", override=True)
        load_dotenv(REPO_ROOT / ".env.local")
        return
    load_dotenv(REPO_ROOT / ".env.local")
    load_dotenv(REPO_ROOT / ".env")


load_repo_env_files()

SECRET_KEY = (
    os.environ.get("DJANGO_SECRET_KEY")
    or os.environ.get("SECRET_KEY")
    or "django-insecure-local-development-key"
)
_debug_raw = os.environ.get("DJANGO_DEBUG", os.environ.get("DEBUG", "false"))
DEBUG = str(_debug_raw).lower() == "true"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1"),
    ).split(",")
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        os.environ.get("CSRF_TRUSTED_ORIGINS", "http://localhost:8990"),
    ).split(",")
    if origin.strip()
]

AUTH_DEV_MODE = os.environ.get("AUTH_DEV_MODE", "false").lower() == "true"

if DEBUG and AUTH_DEV_MODE:
    _local_dev_origins = [
        "http://localhost:8990",
        "http://127.0.0.1:8990",
        "http://localhost:3100",
        "http://127.0.0.1:3100",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.3.180:3100",
    ]
    CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(CSRF_TRUSTED_ORIGINS + _local_dev_origins))
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "application.identity",
    "application.portal",
    "application.gonenkukumi",
    "application.receipt_comparison",
    "application.inventory_order_alert",
    "application.asset_inventory",
    "application.shipment_trend",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "application.portal.interfaces.middleware.AccessApprovalMiddleware",
    "application.portal.interfaces.usage_logging.UsageLoggingMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if not DEBUG:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.csrf",
                "application.portal.interfaces.context_processors.portal_menu",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


def database_config() -> dict[str, object]:
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        parsed = urlparse(database_url)
        if parsed.scheme in {"postgres", "postgresql"}:
            return {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": parsed.path.lstrip("/"),
                "USER": parsed.username or "",
                "PASSWORD": parsed.password or "",
                "HOST": parsed.hostname or "localhost",
                "PORT": str(parsed.port or 5432),
            }
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}

    postgres_db = os.environ.get("POSTGRES_DB")
    if postgres_db:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": postgres_db,
            "USER": os.environ.get("POSTGRES_USER", ""),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": str(os.environ.get("POSTGRES_PORT", "5432")),
        }
    return {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}


DATABASES = {"default": database_config()}
if DATABASES["default"].get("ENGINE", "").endswith("postgresql"):
    DATABASES["default"].setdefault("TEST", {"NAME": "test_worksupportportal"})

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ja"
TIME_ZONE = "Asia/Tokyo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/login"
LOGIN_REDIRECT_URL = "/app"
LOGOUT_REDIRECT_URL = "/login"
AUTH_URL = os.environ.get("AUTH_URL", "http://localhost:8990")
AUTH_PROVIDER = os.environ.get("AUTH_PROVIDER", "desknet").strip().lower()
AUTH_DEV_USERNAME = os.environ.get("AUTH_DEV_USERNAME", "10001")
AUTH_DEV_PASSWORD = os.environ.get("AUTH_DEV_PASSWORD", "dev")
AUTH_DEV_LAST_NAME = os.environ.get("AUTH_DEV_LAST_NAME", "開発")
AUTH_DEV_FIRST_NAME = os.environ.get("AUTH_DEV_FIRST_NAME", "管理者")
DESKNETS_LOGIN_URL = os.environ.get("DESKNETS_LOGIN_URL", "https://maruei01.dn-cloud.com/cgi-bin/dneo/dneo.cgi")
DESKNETS_TIMEOUT_SECONDS = float(os.environ.get("DESKNETS_TIMEOUT_SECONDS", "10"))
DESKNETS_ASSET_INVENTORY_LOGIN_ID = os.environ.get("DESKNETS_ASSET_INVENTORY_LOGIN_ID", "").strip()
DESKNETS_ASSET_INVENTORY_PASSWORD = os.environ.get("DESKNETS_ASSET_INVENTORY_PASSWORD", "")
