from __future__ import annotations

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .base import *
from .base import env


def required(name: str) -> str:
    value = env(name, default="")
    if not value:
        raise ImproperlyConfigured(f"Required production setting is missing: {name}")
    return value


def required_list(name: str) -> list[str]:
    values = env.list(name, default=[])
    if not values:
        raise ImproperlyConfigured(f"Required production setting is missing: {name}")
    return values


SECRET_KEY = required("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = required_list("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = required_list("DJANGO_CSRF_TRUSTED_ORIGINS")
DATABASES = {
    "default": dj_database_url.parse(
        required("DATABASE_URL"),
        conn_max_age=60,
        conn_health_checks=True,
        ssl_require=env.bool("DATABASE_SSL_REQUIRE", default=True),
    )
}
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
AWS_REGION = required("AWS_REGION")
AWS_STORAGE_BUCKET_NAME = required("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = AWS_REGION
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = True
AWS_S3_FILE_OVERWRITE = False
LISTING_MEDIA_ENABLED = True
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "region_name": AWS_REGION,
            "default_acl": None,
            "file_overwrite": False,
            "querystring_auth": True,
        },
    },
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
EMAIL_HOST = required("EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = required("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = required("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = required("SES_FROM_EMAIL")
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)
REPORT_RATE_KEY_SECRET = required("REPORT_RATE_KEY_SECRET")
