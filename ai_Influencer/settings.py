"""Django settings for the persona-portrait API.

Every value a deployment needs to change is read from the environment (see
``.env.example``). Nothing secret is hard-coded: the only literal credential in
this file is a development-only SECRET_KEY that the app refuses to use once
DEBUG is off.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load BASE_DIR/.env if present. Real environment variables always win.
load_dotenv(BASE_DIR / ".env", override=False)

DEV_ONLY_SECRET_KEY = "django-insecure-development-key-do-not-deploy"  # noqa: S105


def env_str(name: str, default: str = "") -> str:
    """Return an environment variable, stripped, falling back to ``default``."""
    return os.environ.get(name, default).strip()


def env_bool(name: str, default: bool) -> bool:
    """Parse a boolean environment variable ('1', 'true', 'yes', 'on')."""
    raw = env_str(name)
    if not raw:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    """Parse an integer environment variable, falling back to ``default``."""
    raw = env_str(name)
    return int(raw) if raw else default


def env_list(name: str, default: list[str]) -> list[str]:
    """Parse a comma-separated environment variable into a list."""
    raw = env_str(name)
    if not raw:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------

DEBUG = env_bool("DJANGO_DEBUG", True)

SECRET_KEY = env_str("DJANGO_SECRET_KEY") or DEV_ONLY_SECRET_KEY
if not DEBUG and SECRET_KEY == DEV_ONLY_SECRET_KEY:
    raise RuntimeError(
        "DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off. "
        'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(50))"'
    )

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1", "0.0.0.0", "testserver"]
)

ROOT_URLCONF = "ai_Influencer.urls"
WSGI_APPLICATION = "ai_Influencer.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "characters",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": env_str("DJANGO_DB_PATH") or BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Generated portraits are user uploads, not static assets: they belong under
# MEDIA_ROOT so Django's storage API owns the paths and the URLs.
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env_str("DJANGO_MEDIA_ROOT") or BASE_DIR / "media")

# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

CHARACTER_PAGE_SIZE = env_int("CHARACTER_PAGE_SIZE", 20)

# Image generation costs money per call, so the create endpoint is throttled
# separately from ordinary reads.
IMAGE_GENERATION_RATE = env_str("IMAGE_GENERATION_RATE", "30/hour")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "characters.pagination.CharacterPagination",
}

# --------------------------------------------------------------------------
# Image provider
# --------------------------------------------------------------------------

OPENAI_API_KEY = env_str("OPENAI_API_KEY")
OPENAI_IMAGE_MODEL = env_str("OPENAI_IMAGE_MODEL", "gpt-image-1")
OPENAI_TIMEOUT_SECONDS = env_int("OPENAI_TIMEOUT_SECONDS", 60)

IMAGE_SIZE = env_str("IMAGE_SIZE", "1024x1024")

# Default to the offline provider so a fresh clone (and `manage.py test`) works
# with no credentials. Setting OPENAI_API_KEY is enough to switch to OpenAI;
# IMAGE_PROVIDER overrides the choice either way.
IMAGE_PROVIDER = env_str("IMAGE_PROVIDER") or ("openai" if OPENAI_API_KEY else "local")
