from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from django.core import mail
from django.core.management import call_command
from django.db import transaction
from django.test.utils import override_settings
from django.utils import timezone

from apps.accounts.models import SellerProfile, User
from apps.catalog.models import Category, Vertical
from apps.core.models import OutboxEvent
from apps.core.outbox import enqueue_event, process_batch
from apps.listings.models import Listing, ListingStatus
from apps.listings.notifications import handle_listing_notification
from apps.listings.selectors import public_listings
from apps.listings.services import expire_due_listings, schedule_listing_reminders
from apps.locations.models import County, State

pytestmark = pytest.mark.django_db


def published_listing(*, expires_at: datetime) -> Listing:
    seller = SellerProfile.objects.create(
        user=User.objects.create_user(email="owner@example.test", password="not-used"),
        display_name="Owner",
    )
    vertical = Vertical.objects.create(name="Autos", slug="autos")
    category = Category.objects.create(vertical=vertical, name="Cars", slug="cars")
    state = State.objects.create(
        fips="48",
        usps_code="TX",
        name="Texas",
        slug="texas",
        is_active=True,
        is_network_enabled=True,
    )
    county = County.objects.create(
        fips="48375",
        state=state,
        name="Potter",
        slug="potter",
        is_active=True,
        is_network_enabled=True,
    )
    return Listing.objects.create(
        seller=seller,
        vertical=vertical,
        category=category,
        state=state,
        county=county,
        city="Amarillo",
        title="Safe public title",
        description="Private details must not be mailed.",
        status=ListingStatus.PUBLISHED,
        published_at=timezone.now(),
        expires_at=expires_at,
    )


def test_enqueue_rolls_back_with_domain_transaction() -> None:
    with pytest.raises(RuntimeError), transaction.atomic():
        enqueue_event(
            event_type="test.event",
            payload={"id": "safe"},
            aggregate_type="test",
            aggregate_reference="safe",
            idempotency_key="rollback-key",
        )
        raise RuntimeError("rollback")

    assert not OutboxEvent.objects.exists()


def test_worker_claim_and_replay_are_idempotent() -> None:
    event = enqueue_event(
        event_type="test.event",
        payload={},
        aggregate_type="test",
        aggregate_reference="safe",
        idempotency_key="once-key",
    )
    handler = Mock()
    with patch("apps.core.outbox._handler_for", return_value=handler):
        assert process_batch(worker_id="worker-a", batch_size=10)["processed"] == 1
        assert process_batch(worker_id="worker-b", batch_size=10)["claimed"] == 0

    event.refresh_from_db()
    assert handler.call_count == 1
    assert event.processed_at is not None
    assert event.delivery_attempts.filter(succeeded=True).count() == 1


@override_settings(OUTBOX_MAX_ATTEMPTS=1)
def test_worker_records_terminal_delivery_failure() -> None:
    event = enqueue_event(
        event_type="test.event",
        payload={},
        aggregate_type="test",
        aggregate_reference="safe",
        idempotency_key="failure-key",
    )
    with patch("apps.core.outbox._handler_for", side_effect=RuntimeError("provider unavailable")):
        assert process_batch(worker_id="worker", batch_size=10)["failed"] == 1

    event.refresh_from_db()
    assert event.failed_at is not None
    assert event.last_error == "Delivery failed (RuntimeError)"
    assert event.delivery_attempts.get().error_message == "Delivery failed (RuntimeError)"


def test_expiration_is_audited_not_public_and_idempotent() -> None:
    listing = published_listing(expires_at=timezone.now() - timedelta(seconds=1))

    assert expire_due_listings(batch_size=10) == 1
    assert expire_due_listings(batch_size=10) == 0
    listing.refresh_from_db()
    assert listing.status == ListingStatus.EXPIRED
    assert not public_listings().filter(pk=listing.pk).exists()
    assert OutboxEvent.objects.get().event_type == "listing.expired"


def test_reminders_use_selected_offsets_once() -> None:
    listing = published_listing(expires_at=timezone.now() + timedelta(days=10))

    assert schedule_listing_reminders() == 3
    assert schedule_listing_reminders() == 0
    reminders = OutboxEvent.objects.order_by("payload__days_remaining")
    assert list(reminders.values_list("payload__days_remaining", flat=True)) == [1, 3, 7]
    assert listing.expires_at is not None
    assert all(
        event.available_at == listing.expires_at - timedelta(days=event.payload["days_remaining"])
        for event in reminders
    )


def test_notification_body_excludes_private_listing_content() -> None:
    listing = published_listing(expires_at=timezone.now() + timedelta(days=7))
    event = enqueue_event(
        event_type="listing.expiration_reminder",
        payload={"listing_id": str(listing.id), "days_remaining": 7},
        aggregate_type="listing",
        aggregate_reference=str(listing.id),
        idempotency_key="email-key",
    )

    handle_listing_notification(event)

    assert len(mail.outbox) == 1
    assert listing.description not in mail.outbox[0].body
    assert listing.seller.user.email not in mail.outbox[0].body
    assert "Safe public title" in mail.outbox[0].body


def test_management_commands_schedule_expire_and_inspect(
    capsys: pytest.CaptureFixture[str],
) -> None:
    published_listing(expires_at=timezone.now() + timedelta(days=10))
    call_command("schedule_listing_reminders")
    call_command("inspect_outbox")
    output = capsys.readouterr().out

    assert "Scheduled 3 listing reminder(s)." in output
    assert "pending=3" in output


def test_process_outbox_command_and_invalid_batch_options(
    capsys: pytest.CaptureFixture[str],
) -> None:
    enqueue_event(
        event_type="test.event",
        payload={},
        aggregate_type="test",
        aggregate_reference="safe",
        idempotency_key="command-key",
    )
    with patch("apps.core.outbox._handler_for", return_value=Mock()):
        call_command("process_outbox", batch_size=10, batches=2)
    call_command("process_outbox", batch_size=0)
    captured = capsys.readouterr()

    assert "outbox claimed=1 processed=1 retry=0 failed=0 skipped=0" in captured.out
    assert "batch-size and batches must be positive." in captured.err


def test_expire_command_and_failed_event_replay(capsys: pytest.CaptureFixture[str]) -> None:
    listing = published_listing(expires_at=timezone.now() - timedelta(seconds=1))
    event = enqueue_event(
        event_type="test.event",
        payload={},
        aggregate_type="test",
        aggregate_reference="safe",
        idempotency_key="replay-key",
    )
    event.failed_at = timezone.now()
    event.save(update_fields=("failed_at",))

    call_command("expire_listings", batch_size=10)
    call_command("inspect_outbox", replay=str(event.id))
    output = capsys.readouterr().out
    listing.refresh_from_db()
    event.refresh_from_db()

    assert "Expired 1 listing(s)." in output
    assert f"Replayed {event.id}." in output
    assert listing.status == ListingStatus.EXPIRED
    assert event.failed_at is None
