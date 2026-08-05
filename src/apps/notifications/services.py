from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User

from .destinations import resolve_destination
from .models import UserNotification

MAX_DESTINATION_ROUTE_LENGTH = 96


def create_notification(  # noqa: PLR0913
    *,
    recipient: User,
    event_type: str,
    title: str,
    body: str,
    idempotency_key: str,
    destination_route: str = "",
    destination_kwargs: Mapping[str, Any] | None = None,
) -> tuple[UserNotification, bool]:
    """
    Create a durable in-app notification within the caller's transaction.

    The idempotency key must be stable for one recipient-visible event. This function
    intentionally does not enqueue email or otherwise interact with the outbox.
    """
    kwargs = dict(destination_kwargs or {})
    resolve_destination(route_name=destination_route, route_kwargs=kwargs)
    _validate_field_lengths(
        event_type=event_type,
        title=title,
        body=body,
        idempotency_key=idempotency_key,
        destination_route=destination_route,
    )
    with transaction.atomic():
        return UserNotification.objects.get_or_create(
            idempotency_key=idempotency_key,
            defaults={
                "recipient": recipient,
                "event_type": event_type,
                "title": title,
                "body": body,
                "destination_route": destination_route,
                "destination_kwargs": kwargs,
            },
        )


def mark_notification_read(
    *, recipient: User, notification_id: UUID | str
) -> UserNotification | None:
    """Mark a single owned notification as read without revealing another user's row."""
    notification = (
        UserNotification.objects.filter(pk=notification_id, recipient=recipient)
        .filter(read_at__isnull=True)
        .first()
    )
    if notification is None:
        return None
    notification.read_at = timezone.now()
    notification.save(update_fields=("read_at", "updated_at"))
    return notification


def mark_all_notifications_read(*, recipient: User) -> int:
    """Mark all unread notifications owned by the recipient as read."""
    now = timezone.now()
    return UserNotification.objects.filter(recipient=recipient, read_at__isnull=True).update(
        read_at=now,
        updated_at=now,
    )


def _validate_field_lengths(
    *,
    event_type: str,
    title: str,
    body: str,
    idempotency_key: str,
    destination_route: str,
) -> None:
    values = (
        (event_type, 96, "event type"),
        (title, 160, "title"),
        (body, 500, "body"),
        (idempotency_key, 200, "idempotency key"),
    )
    for value, maximum, label in values:
        if not value or len(value) > maximum:
            raise ValueError(f"Invalid notification {label}.")
    if len(destination_route) > MAX_DESTINATION_ROUTE_LENGTH:
        raise ValueError("Invalid notification destination route.")
