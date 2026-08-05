from __future__ import annotations

import uuid
from collections.abc import Collection
from typing import Any, ClassVar, Never

from django.contrib.auth.models import AbstractUser
from django.core.validators import URLValidator
from django.db import models
from django.db.models.functions import Lower

from .managers import UserManager


def seller_profile_avatar_path(instance: SellerProfileRevision, filename: str) -> str:
    return f"private-seller-profiles/{instance.seller_profile.public_id}/{uuid.uuid4()}-{filename}"


class PhoneVerificationState(models.TextChoices):
    UNVERIFIED = "unverified", "Unverified"
    VERIFIED = "verified", "Verified"


class AccountStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    CLOSED = "closed", "Closed"


class AccountSecurityEventType(models.TextChoices):
    REGISTERED = "registered", "Registered"
    LOGIN_SUCCEEDED = "login_succeeded", "Login succeeded"
    LOGIN_FAILED = "login_failed", "Login failed"
    PASSWORD_RESET_REQUESTED = "password_reset_requested", "Password reset requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed", "Password reset completed"
    ACCOUNT_SUSPENDED = "account_suspended", "Account suspended"
    ACCOUNT_RESTORED = "account_restored", "Account restored"
    ACCOUNT_CLOSED = "account_closed", "Account closed"
    STAFF_PRIVILEGE_CHANGED = "staff_privilege_changed", "Staff privilege changed"


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None  # type: ignore[assignment]
    email = models.EmailField(unique=True)
    account_status = models.CharField(
        max_length=16,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
        db_index=True,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    objects = UserManager()  # type: ignore[assignment, misc]

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique")
        ]

    def __str__(self) -> str:
        return self.email


class AccountSecurityEvent(models.Model):
    """Append-only account security history; request metadata deliberately excludes headers."""

    actor = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="security_events_as_actor",
    )
    subject = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="security_events_as_subject",
    )
    event_type = models.CharField(
        max_length=40, choices=AccountSecurityEventType.choices, db_index=True
    )
    request_ip_hash = models.CharField(max_length=64, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    request_id = models.CharField(max_length=64, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-occurred_at",)
        indexes = [
            models.Index(fields=("subject", "occurred_at"), name="accounts_security_subject_at"),
            models.Index(fields=("event_type", "occurred_at"), name="accounts_security_type_at"),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} at {self.occurred_at.isoformat()}"

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding:
            raise ValueError("Account security events are immutable.")
        super().save(*args, **kwargs)  # type: ignore[arg-type]

    def delete(self, *_args: object, **_kwargs: object) -> Never:
        raise ValueError("Account security events are immutable.")


class SellerProfile(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="seller_profile")
    display_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=32, blank=True)
    phone_verification_state = models.CharField(
        max_length=16,
        choices=PhoneVerificationState.choices,
        default=PhoneVerificationState.UNVERIFIED,
    )
    current_approved_revision = models.ForeignKey(
        "SellerProfileRevision",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    _original_public_id: uuid.UUID | None = None

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(phone_verification_state=PhoneVerificationState.UNVERIFIED)
                    | ~models.Q(phone="")
                ),
                name="accounts_verified_seller_phone_required",
            )
        ]

    def __str__(self) -> str:
        return self.display_name

    def save(self, *args: object, **kwargs: object) -> None:
        if self._original_public_id is not None and self.public_id != self._original_public_id:
            raise ValueError("Seller profile public IDs are immutable.")
        super().save(*args, **kwargs)  # type: ignore[arg-type]
        self._original_public_id = self.public_id

    @classmethod
    def from_db(
        cls,
        db: str | None,
        field_names: Collection[str],
        values: Collection[Any],
    ) -> SellerProfile:
        profile = super().from_db(db, field_names, values)
        profile._original_public_id = profile.public_id
        return profile


class SellerProfileRevisionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class SellerProfileRevision(models.Model):
    seller_profile = models.ForeignKey(
        SellerProfile,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    status = models.CharField(
        max_length=16,
        choices=SellerProfileRevisionStatus.choices,
        default=SellerProfileRevisionStatus.PENDING,
        db_index=True,
    )
    avatar = models.ImageField(upload_to=seller_profile_avatar_path, blank=True)
    bio = models.TextField(blank=True, max_length=2_000)
    website_url = models.URLField(blank=True, validators=[URLValidator(schemes=["https"])])
    facebook_url = models.URLField(blank=True, validators=[URLValidator(schemes=["https"])])
    instagram_url = models.URLField(blank=True, validators=[URLValidator(schemes=["https"])])
    x_url = models.URLField(blank=True, validators=[URLValidator(schemes=["https"])])
    linkedin_url = models.URLField(blank=True, validators=[URLValidator(schemes=["https"])])
    youtube_url = models.URLField(blank=True, validators=[URLValidator(schemes=["https"])])
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    reviewer = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_seller_profile_revisions",
    )
    review_note = models.TextField(blank=True, max_length=2_000)
    reviewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-submitted_at",)
        indexes = [
            models.Index(
                fields=("seller_profile", "status", "submitted_at"),
                name="acct_profile_revision_queue",
            )
        ]

    def __str__(self) -> str:
        return f"{self.seller_profile} revision submitted {self.submitted_at.isoformat()}"

    @classmethod
    def public_content_field_names(cls) -> tuple[str, ...]:
        return (
            "bio",
            "website_url",
            "facebook_url",
            "instagram_url",
            "x_url",
            "linkedin_url",
            "youtube_url",
        )
