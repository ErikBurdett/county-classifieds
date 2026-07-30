from __future__ import annotations

import hashlib
import hmac

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpRequest

from .models import (
    AccountSecurityEvent,
    AccountSecurityEventType,
    AccountStatus,
    SellerProfile,
    User,
)


def _request_metadata(request: HttpRequest | None) -> dict[str, str]:
    if request is None:
        return {}
    remote_address = request.META.get("REMOTE_ADDR", "")
    return {
        "request_ip_hash": hmac.new(
            settings.SECRET_KEY.encode(), remote_address.encode(), hashlib.sha256
        ).hexdigest()
        if remote_address
        else "",
        "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255],
        "request_id": request.META.get("HTTP_X_REQUEST_ID", "")[:64],
    }


def record_security_event(
    *,
    event_type: AccountSecurityEventType,
    actor: User | None = None,
    subject: User | None = None,
    request: HttpRequest | None = None,
) -> AccountSecurityEvent:
    return AccountSecurityEvent.objects.create(
        event_type=event_type,
        actor=actor,
        subject=subject,
        **_request_metadata(request),
    )


def require_active_account(*, user: User) -> None:
    if user.account_status != AccountStatus.ACTIVE or not user.is_active:
        raise PermissionDenied("This account is not active.")


@transaction.atomic
def register_seller(*, email: str, display_name: str, password: str) -> User:
    user = User.objects.create_user(email=email, password=password)
    SellerProfile.objects.create(user=user, display_name=display_name)
    return user


@transaction.atomic
def change_account_status(
    *,
    actor: User,
    subject: User,
    status: AccountStatus,
    request: HttpRequest | None = None,
) -> User:
    """Change account eligibility through the sole audited status transition."""
    if not actor.is_superuser and not actor.has_perm("accounts.change_user"):
        raise PermissionDenied("You do not have permission to manage account status.")
    locked_subject = User.objects.select_for_update().get(pk=subject.pk)
    if locked_subject.is_superuser and not actor.is_superuser:
        raise PermissionDenied("Only a superuser may change a superuser account.")
    if locked_subject.account_status == status:
        return locked_subject
    locked_subject.account_status = status
    locked_subject.is_active = status == AccountStatus.ACTIVE
    locked_subject.save(update_fields=("account_status", "is_active"))
    event_type = {
        AccountStatus.SUSPENDED: AccountSecurityEventType.ACCOUNT_SUSPENDED,
        AccountStatus.ACTIVE: AccountSecurityEventType.ACCOUNT_RESTORED,
        AccountStatus.CLOSED: AccountSecurityEventType.ACCOUNT_CLOSED,
    }[status]
    record_security_event(
        event_type=event_type,
        actor=actor,
        subject=locked_subject,
        request=request,
    )
    return locked_subject
