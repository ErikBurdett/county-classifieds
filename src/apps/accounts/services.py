from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from .models import (
    AccountSecurityEvent,
    AccountSecurityEventType,
    AccountStatus,
    SellerProfile,
    SellerProfileRevision,
    SellerProfileRevisionStatus,
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
def submit_seller_profile_revision(
    *,
    user: User,
    display_name: str,
    phone: str,
    content: Mapping[str, str],
    avatar: UploadedFile | None = None,
) -> SellerProfileRevision:
    """Update private attribution details and submit public profile content for review."""
    require_active_account(user=user)
    profile, _ = SellerProfile.objects.select_for_update().get_or_create(
        user=user,
        defaults={"display_name": display_name, "phone": phone},
    )
    if profile.display_name != display_name or profile.phone != phone:
        profile.display_name = display_name
        profile.phone = phone
        profile.save(update_fields=("display_name", "phone", "updated_at"))
    revision = SellerProfileRevision(seller_profile=profile, avatar=avatar, **dict(content))
    revision.full_clean()
    revision.save()
    return revision


@transaction.atomic
def review_seller_profile_revision(
    *,
    revision_id: int,
    reviewer: User,
    status: SellerProfileRevisionStatus,
    note: str,
) -> SellerProfileRevision:
    """Record a staff review and point the seller profile at approved public content."""
    if status not in {
        SellerProfileRevisionStatus.APPROVED,
        SellerProfileRevisionStatus.REJECTED,
    }:
        raise ValueError("Seller profile revisions may only be approved or rejected.")
    if not reviewer.is_staff or not (
        reviewer.is_superuser or reviewer.has_perm("accounts.change_sellerprofilerevision")
    ):
        raise PermissionDenied("You do not have permission to review seller profile revisions.")

    revision = (
        SellerProfileRevision.objects.select_for_update()
        .select_related("seller_profile")
        .get(pk=revision_id)
    )
    if revision.status != SellerProfileRevisionStatus.PENDING:
        raise ValueError("Only pending seller profile revisions may be reviewed.")

    revision.status = status
    revision.reviewer = reviewer
    revision.review_note = note
    revision.reviewed_at = timezone.now()
    revision.save(update_fields=("status", "reviewer", "review_note", "reviewed_at"))
    if status == SellerProfileRevisionStatus.APPROVED:
        profile = SellerProfile.objects.select_for_update().get(pk=revision.seller_profile_id)
        profile.current_approved_revision = revision
        profile.save(update_fields=("current_approved_revision", "updated_at"))
    return revision


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
