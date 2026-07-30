from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.listings.notifications import handle_listing_notification

from .models import OutboxDeliveryAttempt, OutboxEvent

logger = logging.getLogger(__name__)

EventHandler = Callable[[OutboxEvent], None]
MAX_ERROR_LENGTH = 200


def enqueue_event(  # noqa: PLR0913
    *,
    event_type: str,
    payload: dict[str, Any],
    aggregate_type: str,
    aggregate_reference: str,
    idempotency_key: str,
    available_at: Any | None = None,
) -> OutboxEvent:
    """Create a JSON-safe event within an already-open domain transaction."""
    return OutboxEvent.objects.create(
        event_type=event_type,
        payload=payload,
        aggregate_type=aggregate_type,
        aggregate_reference=aggregate_reference,
        idempotency_key=idempotency_key,
        available_at=available_at or timezone.now(),
    )


def _retry_delay(attempt_count: int) -> timedelta:
    return timedelta(seconds=min(300, 2 ** min(attempt_count, 8)))


def claim_events(*, worker_id: str, batch_size: int) -> list[OutboxEvent]:
    """Lease available events; PostgreSQL workers skip each other's locked rows."""
    now = timezone.now()
    lease_cutoff = now - timedelta(seconds=settings.OUTBOX_LEASE_SECONDS)
    with transaction.atomic():
        events = list(
            OutboxEvent.objects.select_for_update(skip_locked=True)
            .filter(processed_at__isnull=True, failed_at__isnull=True, available_at__lte=now)
            .filter(Q(locked_at__isnull=True) | Q(locked_at__lt=lease_cutoff))
            .order_by("available_at", "created_at")[:batch_size]
        )
        for event in events:
            event.attempt_count += 1
            event.locked_at = now
            event.locked_by = worker_id
            event.save(update_fields=("attempt_count", "locked_at", "locked_by"))
            OutboxDeliveryAttempt.objects.create(
                event=event,
                attempt_number=event.attempt_count,
                started_at=now,
            )
    return events


def _handler_for(event_type: str) -> EventHandler:
    handlers: dict[str, EventHandler] = {
        "listing.approved": handle_listing_notification,
        "listing.changes_requested": handle_listing_notification,
        "listing.rejected": handle_listing_notification,
        "listing.sold": handle_listing_notification,
        "listing.expired": handle_listing_notification,
        "listing.expiration_reminder": handle_listing_notification,
    }
    try:
        return handlers[event_type]
    except KeyError as error:
        raise ValueError("Unsupported outbox event type.") from error


def deliver_event(*, event_id: Any, worker_id: str) -> str:
    """Deliver one leased event idempotently and persist its result."""
    with transaction.atomic():
        event = OutboxEvent.objects.select_for_update().get(pk=event_id)
        if event.processed_at is not None or event.failed_at is not None:
            return "skipped"
        if event.locked_by != worker_id:
            return "skipped"
        attempt = OutboxDeliveryAttempt.objects.select_for_update().get(
            event=event, attempt_number=event.attempt_count
        )
    try:
        _handler_for(event.event_type)(event)
    except Exception as error:  # noqa: BLE001 - handlers must never strand a leased event.
        safe_error = f"Delivery failed ({type(error).__name__})"[:MAX_ERROR_LENGTH]
        now = timezone.now()
        with transaction.atomic():
            event = OutboxEvent.objects.select_for_update().get(pk=event_id)
            attempt = OutboxDeliveryAttempt.objects.select_for_update().get(
                event=event, attempt_number=event.attempt_count
            )
            attempt.finished_at = now
            attempt.error_message = safe_error
            attempt.save(update_fields=("finished_at", "error_message"))
            event.last_error = safe_error
            event.locked_at = None
            event.locked_by = ""
            if event.attempt_count >= settings.OUTBOX_MAX_ATTEMPTS:
                event.failed_at = now
                outcome = "failed"
            else:
                event.available_at = now + _retry_delay(event.attempt_count)
                outcome = "retry"
            event.save(
                update_fields=(
                    "last_error",
                    "locked_at",
                    "locked_by",
                    "available_at",
                    "failed_at",
                )
            )
        logger.warning(
            "outbox_delivery_failed",
            extra={"event_id": str(event_id), "event_type": event.event_type, "outcome": outcome},
        )
        return outcome
    now = timezone.now()
    with transaction.atomic():
        event = OutboxEvent.objects.select_for_update().get(pk=event_id)
        attempt = OutboxDeliveryAttempt.objects.select_for_update().get(
            event=event, attempt_number=event.attempt_count
        )
        attempt.finished_at = now
        attempt.succeeded = True
        attempt.save(update_fields=("finished_at", "succeeded"))
        event.processed_at = now
        event.locked_at = None
        event.locked_by = ""
        event.last_error = ""
        event.save(update_fields=("processed_at", "locked_at", "locked_by", "last_error"))
    logger.info(
        "outbox_delivery_succeeded",
        extra={"event_id": str(event_id), "event_type": event.event_type},
    )
    return "processed"


def process_batch(*, worker_id: str, batch_size: int) -> dict[str, int]:
    counts = {"claimed": 0, "processed": 0, "retry": 0, "failed": 0, "skipped": 0}
    for event in claim_events(worker_id=worker_id, batch_size=batch_size):
        counts["claimed"] += 1
        counts[deliver_event(event_id=event.id, worker_id=worker_id)] += 1
    logger.info("outbox_batch_complete", extra=counts)
    return counts


def replay_failed_event(*, event_id: Any) -> OutboxEvent:
    """Make a terminally failed event eligible again without changing its key."""
    with transaction.atomic():
        event = OutboxEvent.objects.select_for_update().get(pk=event_id)
        if event.processed_at is not None:
            return event
        event.failed_at = None
        event.available_at = timezone.now()
        event.locked_at = None
        event.locked_by = ""
        event.last_error = ""
        event.save(
            update_fields=("failed_at", "available_at", "locked_at", "locked_by", "last_error")
        )
    return event
