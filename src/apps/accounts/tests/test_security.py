from __future__ import annotations

import pytest
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse

from apps.accounts.models import AccountSecurityEvent, AccountSecurityEventType, AccountStatus, User
from apps.accounts.services import change_account_status

pytestmark = pytest.mark.django_db


def test_staff_group_provisioning_is_debug_only() -> None:
    with override_settings(DEBUG=False), pytest.raises(CommandError):
        call_command("provision_staff_groups")


def test_password_reset_response_does_not_enumerate_accounts(client: Client) -> None:
    User.objects.create_user(email="known@example.com", password="test-password")
    known = client.post(reverse("accounts:password_reset"), {"email": "known@example.com"})
    unknown = client.post(reverse("accounts:password_reset"), {"email": "unknown@example.com"})

    assert known.status_code == unknown.status_code == 302
    assert known["Location"] == unknown["Location"] == reverse("accounts:password_reset_done")
    assert len(mail.outbox) == 1
    assert (
        AccountSecurityEvent.objects.filter(
            event_type=AccountSecurityEventType.PASSWORD_RESET_REQUESTED
        ).count()
        == 2
    )


def test_suspension_invalidates_login_and_records_audit(client: Client) -> None:
    actor = User.objects.create_superuser(email="admin@example.com", password="test-password")
    subject = User.objects.create_user(email="seller@example.com", password="test-password")

    change_account_status(actor=actor, subject=subject, status=AccountStatus.SUSPENDED)

    subject.refresh_from_db()
    assert not subject.is_active
    assert subject.account_status == AccountStatus.SUSPENDED
    assert not client.login(username=subject.email, password="test-password")
    assert AccountSecurityEvent.objects.filter(
        actor=actor,
        subject=subject,
        event_type=AccountSecurityEventType.ACCOUNT_SUSPENDED,
    ).exists()
