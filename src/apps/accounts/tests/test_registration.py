from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import SellerProfile, User

pytestmark = pytest.mark.django_db


def registration_data(**overrides: str) -> dict[str, str]:
    return {
        "email": " New.Seller@EXAMPLE.COM ",
        "display_name": "  New   Seller  ",
        "password1": "secure-test-password-123",
        "password2": "secure-test-password-123",
        **overrides,
    }


def test_register_page_renders(client: Client) -> None:
    response = client.get(reverse("accounts:register"))

    assert response.status_code == 200
    assert "Create your account" in response.content.decode()


def test_registration_creates_profile_logs_user_in_and_redirects(client: Client) -> None:
    response = client.post(reverse("accounts:register"), registration_data())

    user = User.objects.get(email="new.seller@example.com")
    assert response.status_code == 302
    assert response["Location"] == reverse("listings:dashboard")
    assert user.check_password("secure-test-password-123")
    assert SellerProfile.objects.get(user=user).display_name == "New Seller"
    assert client.session["_auth_user_id"] == str(user.pk)


def test_registration_rejects_duplicate_normalized_email(client: Client) -> None:
    User.objects.create_user(email="new.seller@example.com", password="existing-password")

    response = client.post(reverse("accounts:register"), registration_data())

    assert response.status_code == 200
    assert "An account with this email already exists." in response.content.decode()
    assert User.objects.count() == 1
    assert not SellerProfile.objects.exists()


def test_registration_rejects_duplicate_normalized_display_name(client: Client) -> None:
    user = User.objects.create_user(email="existing@example.com", password="existing-password")
    SellerProfile.objects.create(user=user, display_name="Existing Seller")

    response = client.post(
        reverse("accounts:register"),
        registration_data(email="new@example.com", display_name=" existing   seller "),
    )

    assert response.status_code == 200
    assert "This display name is already in use." in response.content.decode()
    assert User.objects.count() == 1


def test_registration_rejects_invalid_password(client: Client) -> None:
    response = client.post(
        reverse("accounts:register"),
        registration_data(password2="different-password-123"),
    )

    assert response.status_code == 200
    assert "password fields" in response.content.decode()
    assert not User.objects.exists()
    assert not SellerProfile.objects.exists()


def test_registration_ignores_untrusted_next_redirect(client: Client) -> None:
    response = client.post(
        f"{reverse('accounts:register')}?next=https://attacker.example/",
        registration_data(),
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("listings:dashboard")
