from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator
from types import ModuleType

import pytest
from django.core.exceptions import ImproperlyConfigured
from pytest import MonkeyPatch

REQUIRED_PRODUCTION_ENVIRONMENT = {
    "DJANGO_SECRET_KEY": "production-check-secret",
    "DJANGO_ALLOWED_HOSTS": "market.example.com",
    "DJANGO_CSRF_TRUSTED_ORIGINS": "https://market.example.com",
    "DATABASE_URL": "postgresql://marketplace:password@example.com:5432/marketplace",
    "AWS_REGION": "us-east-1",
    "AWS_STORAGE_BUCKET_NAME": "marketplace-media",
    "EMAIL_HOST": "email-smtp.us-east-1.amazonaws.com",
    "EMAIL_HOST_USER": "smtp-user",
    "EMAIL_HOST_PASSWORD": "smtp-password",
    "SES_FROM_EMAIL": "market@example.com",
    "REPORT_RATE_KEY_SECRET": "production-report-rate-secret",
}


def load_production_settings(monkeypatch: MonkeyPatch) -> ModuleType:
    for name, value in REQUIRED_PRODUCTION_ENVIRONMENT.items():
        monkeypatch.setenv(name, value)
    sys.modules.pop("config.settings.production", None)
    return importlib.import_module("config.settings.production")


@pytest.fixture
def production_settings(monkeypatch: MonkeyPatch) -> Iterator[ModuleType]:
    yield load_production_settings(monkeypatch)
    sys.modules.pop("config.settings.production", None)


def test_production_uses_private_s3_storage(production_settings: ModuleType) -> None:
    assert production_settings.LISTING_MEDIA_ENABLED is True
    assert production_settings.AWS_QUERYSTRING_AUTH is True
    assert production_settings.STORAGES["default"]["BACKEND"] == "storages.backends.s3.S3Storage"


def test_production_rejects_empty_host_allowlist(monkeypatch: MonkeyPatch) -> None:
    for name, value in REQUIRED_PRODUCTION_ENVIRONMENT.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "")
    sys.modules.pop("config.settings.production", None)

    with pytest.raises(ImproperlyConfigured, match="DJANGO_ALLOWED_HOSTS"):
        importlib.import_module("config.settings.production")

    sys.modules.pop("config.settings.production", None)
