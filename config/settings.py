from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent


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


load_dotenv(BASE_DIR / ".env.production", override=True)
load_dotenv(BASE_DIR / ".env.local")
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-local-development-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [host.strip() for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]

AUTH_DEV_MODE = os.environ.get("AUTH_DEV_MODE", "false").lower() == "true"

if DEBUG and AUTH_DEV_MODE:
    _local_dev_origins = [
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
    "apps.identity",
    "apps.portal",
    "apps.gonenkukumi",
    "apps.receipt_comparison",
    "apps.inventory_order_alert",
    "apps.asset_inventory",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.portal.middleware.AccessApprovalMiddleware",
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
                "apps.portal.context_processors.portal_menu",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


def database_config() -> dict[str, object]:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}

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
AUTH_URL = os.environ.get("AUTH_URL", "http://localhost:3000")
AUTH_PROVIDER = os.environ.get("AUTH_PROVIDER", "desknet").strip().lower()
AUTH_DEV_USERNAME = os.environ.get("AUTH_DEV_USERNAME", "10001")
AUTH_DEV_PASSWORD = os.environ.get("AUTH_DEV_PASSWORD", "dev")
AUTH_DEV_LAST_NAME = os.environ.get("AUTH_DEV_LAST_NAME", "開発")
AUTH_DEV_FIRST_NAME = os.environ.get("AUTH_DEV_FIRST_NAME", "管理者")
DESKNETS_LOGIN_URL = os.environ.get("DESKNETS_LOGIN_URL", "https://maruei01.dn-cloud.com/cgi-bin/dneo/dneo.cgi")
DESKNETS_TIMEOUT_SECONDS = float(os.environ.get("DESKNETS_TIMEOUT_SECONDS", "10"))
