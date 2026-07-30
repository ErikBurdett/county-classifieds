from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Count, Min, Q
from django.utils import timezone

from apps.billing.models import Order, OrderStatus
from apps.catalog.models import Category, ListingKind, ListingProduct, Vertical
from apps.core.models import OutboxEvent
from apps.listings.models import Listing, ListingStatus, ModerationActionType
from apps.locations.models import County, State
from apps.policies.models import PolicyDocument, PolicyDocumentStatus


@dataclass(frozen=True)
class ManagementDashboard:
    listing_counts: tuple[tuple[str, int], ...]
    moderation_assigned: int
    moderation_unassigned: int
    moderation_escalated: int
    outbox_pending: int
    outbox_failed: int
    oldest_pending_age: timedelta | None
    orders_requiring_review: int
    refunds_requiring_review: int
    active_policies: int
    active_states: int
    active_counties: int
    active_verticals: int
    active_categories: int
    active_listing_kinds: int
    active_products: int


def management_dashboard() -> ManagementDashboard:
    """Return bounded operational aggregates without materializing domain records."""
    counts_by_status = {
        row["status"]: row["count"]
        for row in Listing.objects.values("status").annotate(count=Count("id"))
    }
    listing_counts = tuple(
        (label, counts_by_status.get(status, 0)) for status, label in ListingStatus.choices
    )
    moderation = Listing.objects.filter(status=ListingStatus.IN_REVIEW).aggregate(
        assigned=Count("id", filter=Q(assigned_moderator__isnull=False)),
        unassigned=Count("id", filter=Q(assigned_moderator__isnull=True)),
        escalated=Count(
            "id",
            filter=Q(moderation_actions__action_type=ModerationActionType.ESCALATED),
            distinct=True,
        ),
    )
    outbox = OutboxEvent.objects.aggregate(
        pending=Count("id", filter=Q(processed_at__isnull=True, failed_at__isnull=True)),
        failed=Count("id", filter=Q(failed_at__isnull=False)),
        oldest=Min("available_at", filter=Q(processed_at__isnull=True, failed_at__isnull=True)),
    )
    order_counts = Order.objects.aggregate(
        orders_requiring_review=Count(
            "id",
            filter=Q(status__in=(OrderStatus.PENDING, OrderStatus.PAYMENT_FAILED)),
        ),
        refunds_requiring_review=Count("id", filter=Q(status=OrderStatus.REFUND_PENDING)),
    )
    catalog_counts = {
        "active_verticals": Vertical.objects.filter(is_active=True).count(),
        "active_categories": Category.objects.filter(is_active=True).count(),
        "active_listing_kinds": ListingKind.objects.filter(is_active=True).count(),
        "active_products": ListingProduct.objects.filter(is_active=True).count(),
    }
    geography_counts = {
        "active_states": State.objects.filter(is_active=True).count(),
        "active_counties": County.objects.filter(is_active=True).count(),
    }
    oldest = outbox["oldest"]
    return ManagementDashboard(
        listing_counts=listing_counts,
        moderation_assigned=moderation["assigned"],
        moderation_unassigned=moderation["unassigned"],
        moderation_escalated=moderation["escalated"],
        outbox_pending=outbox["pending"],
        outbox_failed=outbox["failed"],
        oldest_pending_age=None if oldest is None else max(timezone.now() - oldest, timedelta()),
        orders_requiring_review=order_counts["orders_requiring_review"],
        refunds_requiring_review=order_counts["refunds_requiring_review"],
        active_policies=PolicyDocument.objects.filter(status=PolicyDocumentStatus.ACTIVE).count(),
        **geography_counts,
        **catalog_counts,
    )
