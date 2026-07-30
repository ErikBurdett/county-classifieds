from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def create_user(*, email: str, staff: bool = False, password: str = "test-password") -> User:
    return User.objects.create_user(email=email, password=password, is_staff=staff)


def test_anonymous_management_access_redirects_to_staff_login(client: Client) -> None:
    response = client.get(reverse("management_console:dashboard"))

    assert response.status_code == 302
    assert response["Location"].startswith(f"{reverse('management_console:login')}?next=")


def test_nonstaff_cannot_access_or_log_into_management(client: Client) -> None:
    user = create_user(email="seller@example.com")
    client.force_login(user)

    response = client.get(reverse("management_console:dashboard"))
    assert response.status_code == 302
    assert response["Location"] == reverse("management_console:login")
    assert "_auth_user_id" not in client.session

    response = client.post(
        reverse("management_console:login"),
        {"username": user.email, "password": "test-password"},
    )
    assert response.status_code == 200
    assert "Please enter a correct email and password." in response.content.decode()
    assert "_auth_user_id" not in client.session


def test_staff_login_dashboard_and_safe_next(client: Client) -> None:
    staff = create_user(email="staff@example.com", staff=True)
    login_url = reverse("management_console:login")

    unsafe = client.post(
        f"{login_url}?next=https://attacker.example/",
        {"username": staff.email, "password": "test-password", "next": "https://attacker.example/"},
    )
    assert unsafe.status_code == 302
    assert unsafe["Location"] == reverse("management_console:dashboard")

    client.post(reverse("management_console:logout"))
    safe = client.post(
        f"{login_url}?next=/manage/",
        {"username": staff.email, "password": "test-password", "next": "/manage/"},
    )
    assert safe.status_code == 302
    assert safe["Location"] == "/manage/"
    assert client.get(reverse("management_console:dashboard")).status_code == 200


def test_staff_login_requires_csrf() -> None:
    client = Client(enforce_csrf_checks=True)
    staff = create_user(email="staff@example.com", staff=True)
    login_url = reverse("management_console:login")

    assert (
        client.post(login_url, {"username": staff.email, "password": "test-password"}).status_code
        == 403
    )
    response = client.get(login_url)
    csrf_token = response.cookies["csrftoken"].value
    assert (
        client.post(
            login_url,
            {
                "username": staff.email,
                "password": "test-password",
                "csrfmiddlewaretoken": csrf_token,
            },
            HTTP_REFERER="http://testserver/manage/login/",
        ).status_code
        == 302
    )


def test_dashboard_uses_bounded_aggregate_query_budget(client: Client) -> None:
    staff = create_user(email="staff@example.com", staff=True)
    client.force_login(staff)

    with CaptureQueriesContext(connection) as queries:
        response = client.get(reverse("management_console:dashboard"))

    assert response.status_code == 200
    assert "Operational summaries only." in response.content.decode()
    assert len(queries) <= 15


def test_dashboard_links_follow_model_permissions(client: Client) -> None:
    staff = create_user(email="staff@example.com", staff=True)
    client.force_login(staff)

    no_permissions = client.get(reverse("management_console:dashboard"))
    assert "Moderation queue" not in no_permissions.content.decode()
    assert "Listing reports" not in no_permissions.content.decode()
    assert "Billing reconciliation" not in no_permissions.content.decode()

    staff.user_permissions.add(
        Permission.objects.get(content_type__app_label="listings", codename="moderate_listing"),
        Permission.objects.get(content_type__app_label="reports", codename="triage_listingreport"),
        Permission.objects.get(content_type__app_label="billing", codename="view_order"),
        Permission.objects.get(content_type__app_label="policies", codename="view_policydocument"),
    )
    permitted = client.get(reverse("management_console:dashboard"))
    content = permitted.content.decode()
    assert "Moderation queue" in content
    assert "Listing reports" in content
    assert reverse("reports:queue") in content
    assert "Billing reconciliation" in content
    assert "Policy documents" in content
    assert "Outbox operations" not in content


def test_billing_reconciliation_requires_order_view_permission(client: Client) -> None:
    staff = create_user(email="staff@example.com", staff=True)
    client.force_login(staff)

    assert client.get(reverse("billing:reconciliation")).status_code == 403
    staff.user_permissions.add(
        Permission.objects.get(content_type__app_label="billing", codename="view_order")
    )
    assert client.get(reverse("billing:reconciliation")).status_code == 200


def test_seed_demo_staff_is_idempotent_and_never_outputs_password(tmp_path: Path) -> None:
    output = StringIO()
    with pytest.raises(CommandError):
        call_command("seed_demo_staff", stdout=output)

    with override_settings(DEBUG=True, PROJECT_ROOT=tmp_path):
        call_command("seed_demo_staff", stdout=output)
        call_command("seed_demo_staff", stdout=output)

    user = User.objects.get(email="admin@local.test")
    assert user.is_staff
    assert user.is_superuser
    assert user.check_password("LocalStaffOnly-ChangeMe-2026!")
    assert "LocalStaffOnly-ChangeMe-2026!" not in output.getvalue()
    assert "admin@local.test" in (tmp_path / "tmp" / "test-accounts.txt").read_text()


def test_seed_demo_staff_preserves_existing_account(tmp_path: Path) -> None:
    existing = create_user(email="admin@local.test", password="existing-password")
    with override_settings(DEBUG=True, PROJECT_ROOT=tmp_path):
        call_command("seed_demo_staff")

    existing.refresh_from_db()
    assert existing.check_password("existing-password")
    assert not existing.is_staff
    assert not existing.is_superuser


def test_seed_demo_staff_merges_marketplace_credentials(tmp_path: Path) -> None:
    credentials = tmp_path / "tmp" / "test-accounts.txt"
    credentials.parent.mkdir()
    credentials.write_text(
        "telephoneheater@local.test: LocalDemoOnly-ChangeMe-2026!\n",
        encoding="utf-8",
    )

    with override_settings(DEBUG=True, PROJECT_ROOT=tmp_path):
        call_command("seed_demo_staff")

    saved = credentials.read_text(encoding="utf-8")
    assert "telephoneheater@local.test: LocalDemoOnly-ChangeMe-2026!" in saved
    assert "admin@local.test: LocalStaffOnly-ChangeMe-2026!" in saved
