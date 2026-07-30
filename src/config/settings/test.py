from __future__ import annotations

from .base import *
from .base import env

SECRET_KEY = "test-only-secret"
DEBUG = False
LISTING_MEDIA_ENABLED = True
ALLOWED_HOSTS = ["testserver", "localhost"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# The default allows fast, Docker-free local test runs. CI explicitly uses PostgreSQL
# to validate PostgreSQL migrations and constraints.
if env.bool("USE_POSTGRES_TEST_DATABASE", default=False):
    DATABASES["default"]["TEST"] = {"NAME": "marketplace_test"}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
