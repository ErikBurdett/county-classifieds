from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def test_create_user_normalizes_email() -> None:
    user = User.objects.create_user(email=" Person@EXAMPLE.COM ", password="test-password")
    assert user.email == "person@example.com"
    assert user.check_password("test-password")
    assert not user.is_staff


def test_case_insensitive_email_constraint() -> None:
    User.objects.create_user(email="person@example.com", password="test-password")
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create(email="PERSON@example.com")


def test_create_superuser_sets_staff_flags() -> None:
    user = User.objects.create_superuser(email="admin@example.com", password="test-password")
    assert user.is_staff
    assert user.is_superuser
