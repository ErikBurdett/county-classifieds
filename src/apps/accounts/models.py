from __future__ import annotations

import uuid
from typing import ClassVar, Never

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

from .managers import UserManager


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
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="seller_profile")
    display_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=32, blank=True)
    phone_verification_state = models.CharField(
        max_length=16,
        choices=PhoneVerificationState.choices,
        default=PhoneVerificationState.UNVERIFIED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
