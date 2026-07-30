from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction

from apps.accounts.forms import MarketplaceUserChangeForm, MarketplaceUserCreationForm
from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def test_create_user_normalizes_email() -> None:
    user = User.objects.create_user(email=" Person@EXAMPLE.COM ", password="test-password")
    assert user.email == "person@example.com"
    assert user.check_password("test-password")
    assert not user.is_staff
    assert str(user) == "person@example.com"


def test_create_user_requires_email() -> None:
    with pytest.raises(ValueError, match="email address"):
        User.objects.create_user(email="", password="test-password")


def test_case_insensitive_email_constraint() -> None:
    User.objects.create_user(email="person@example.com", password="test-password")
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create(email="PERSON@example.com")


def test_user_creation_form_normalizes_email() -> None:
    form = MarketplaceUserCreationForm(
        data={
            "email": " Person@EXAMPLE.COM ",
            "password1": "correct-horse-battery-staple-123",
            "password2": "correct-horse-battery-staple-123",
        }
    )
    assert form.is_valid(), form.errors
    user = form.save()
    assert user.email == "person@example.com"


def test_user_change_form_normalizes_email() -> None:
    user = User.objects.create_user(email="person@example.com", password="test-password")
    form = MarketplaceUserChangeForm(
        instance=user,
        data={
            "email": " Renamed@EXAMPLE.COM ",
            "password": user.password,
            "is_active": True,
            "date_joined": user.date_joined,
        },
    )
    assert form.is_valid(), form.errors
    changed = form.save()
    assert changed.email == "renamed@example.com"


def test_create_superuser_sets_staff_flags() -> None:
    user = User.objects.create_superuser(email="admin@example.com", password="test-password")
    assert user.is_staff
    assert user.is_superuser


@pytest.mark.parametrize("field", ["is_staff", "is_superuser"])
def test_create_superuser_rejects_missing_required_flag(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        User.objects.create_superuser(
            email="admin@example.com",
            password="test-password",
            **{field: False},
        )
