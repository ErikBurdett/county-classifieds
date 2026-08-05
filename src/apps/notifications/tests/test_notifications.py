from __future__ import annotations

from uuid import uuid4

import pytest
from django.db import IntegrityError, transaction
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.notifications.destinations import resolve_destination
from apps.notifications.models import UserNotification
from apps.notifications.services import (
    create_notification,
    mark_all_notifications_read,
    mark_notification_read,
)

pytestmark = pytest.mark.django_db


def notification_for(*, recipient: User, key: str = "test-key") -> UserNotification:
    notification, _ = create_notification(
        recipient=recipient,
        event_type="listing.approved",
        title="Listing approved",
        body="Your listing is ready.",
        idempotency_key=key,
        destination_route="listings:dashboard",
    )
    return notification


def test_creation_is_idempotent_and_transactional() -> None:
    recipient = User.objects.create_user(email="recipient@example.test", password="password")

    created, was_created = create_notification(
        recipient=recipient,
        event_type="listing.approved",
        title="Listing approved",
        body="Your listing is ready.",
        idempotency_key="listing-approved:1",
        destination_route="listings:dashboard",
    )
    repeated, was_repeated_created = create_notification(
        recipient=recipient,
        event_type="listing.approved",
        title="Listing approved",
        body="Your listing is ready.",
        idempotency_key="listing-approved:1",
        destination_route="listings:dashboard",
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        create_notification(
            recipient=recipient,
            event_type="listing.rejected",
            title="Listing needs attention",
            body="Review the status.",
            idempotency_key="rolled-back",
        )
        raise IntegrityError

    assert was_created is True
    assert was_repeated_created is False
    assert repeated == created
    assert not UserNotification.objects.filter(idempotency_key="rolled-back").exists()


def test_destination_resolution_rejects_arbitrary_urls() -> None:
    listing_id = uuid4()

    destination = resolve_destination(
        route_name="listings:owner_listing_detail",
        route_kwargs={"listing_id": listing_id},
    )
    assert destination is not None
    assert destination.endswith(f"/dashboard/listings/{listing_id}/detail/")
    with pytest.raises(ValueError, match="Unsupported notification destination"):
        resolve_destination(route_name="https://attacker.example", route_kwargs={})
    with pytest.raises(ValueError, match="Invalid notification destination arguments"):
        resolve_destination(route_name="listings:dashboard", route_kwargs={"next": "/admin/"})


def test_invalid_persisted_destination_never_resolves_to_a_redirect() -> None:
    recipient = User.objects.create_user(email="recipient@example.test", password="password")
    notification = UserNotification.objects.create(
        recipient=recipient,
        event_type="test.event",
        title="Safe",
        body="Safe",
        idempotency_key="invalid-persisted-destination",
        destination_route="https://attacker.example",
        destination_kwargs={},
    )

    assert notification.destination_url is None


def test_marking_read_requires_recipient_ownership(client: Client) -> None:
    recipient = User.objects.create_user(email="recipient@example.test", password="password")
    other_user = User.objects.create_user(email="other@example.test", password="password")
    notification = notification_for(recipient=recipient)
    client.force_login(other_user)

    response = client.post(
        reverse("notifications:mark_read", kwargs={"notification_id": notification.id})
    )

    notification.refresh_from_db()
    assert response.status_code == 302
    assert response["Location"] == reverse("notifications:feed")
    assert notification.read_at is None


def test_visiting_owned_notification_marks_it_read_and_uses_safe_destination(
    client: Client,
) -> None:
    recipient = User.objects.create_user(email="recipient@example.test", password="password")
    notification = notification_for(recipient=recipient)
    client.force_login(recipient)

    response = client.get(
        reverse("notifications:visit", kwargs={"notification_id": notification.id})
    )

    notification.refresh_from_db()
    assert response.status_code == 302
    assert response["Location"] == reverse("listings:dashboard")
    assert notification.read_at is not None


def test_feed_is_recipient_scoped_and_mark_all_read(client: Client) -> None:
    recipient = User.objects.create_user(email="recipient@example.test", password="password")
    other_user = User.objects.create_user(email="other@example.test", password="password")
    owned = notification_for(recipient=recipient, key="owned")
    create_notification(
        recipient=other_user,
        event_type="account.changed",
        title="Other user's private update",
        body="This must not render.",
        idempotency_key="other",
    )
    client.force_login(recipient)

    response = client.get(reverse("notifications:feed"))
    mark_all_response = client.post(reverse("notifications:mark_all_read"))

    owned.refresh_from_db()
    assert response.status_code == 200
    assert "Listing approved" in response.content.decode()
    assert "Other user's private update" not in response.content.decode()
    assert mark_all_response.status_code == 302
    assert owned.read_at is not None
    assert mark_all_notifications_read(recipient=recipient) == 0


def test_unread_notification_is_marked_read_by_service() -> None:
    recipient = User.objects.create_user(email="recipient@example.test", password="password")
    notification = notification_for(recipient=recipient)

    marked = mark_notification_read(recipient=recipient, notification_id=notification.id)

    assert marked is not None
    assert marked.read_at is not None
