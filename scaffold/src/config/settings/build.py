from __future__ import annotations

from .base import *

SECRET_KEY = "container-build-only"
ALLOWED_HOSTS: list[str] = []
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
