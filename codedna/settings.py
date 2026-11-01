import os
import shutil
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-this-before-deployment")
DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "testserver",
    ".vercel.app",
    "*",
]

CSRF_TRUSTED_ORIGINS = [
    "https://*.vercel.app",
    "https://djangolabproject.vercel.app",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "codedna.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

WSGI_APPLICATION = "codedna.wsgi.application"

# Serverless environment detection (Vercel / AWS Lambda)
IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

if IS_VERCEL:
    # On Vercel (Linux / AWS Lambda), the deployment directory is read-only.
    # The system temp directory (/tmp) is the only writable storage.
    temp_dir = Path(tempfile.gettempdir())
    DB_PATH = temp_dir / "db.sqlite3"
    seed_db = BASE_DIR / "db.sqlite3"
    # Copy pre-migrated seed database from repo to temp storage on cold start
    if not DB_PATH.exists() and seed_db.exists():
        try:
            shutil.copyfile(seed_db, DB_PATH)
        except Exception as exc:
            print(f"Notice: Failed to copy seed db: {exc}")

    MEDIA_ROOT = temp_dir / "media"
    try:
        MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
else:
    DB_PATH = BASE_DIR / "db.sqlite3"
    MEDIA_ROOT = BASE_DIR / "media"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(DB_PATH),
    }
}

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

MEDIA_URL = "media/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
