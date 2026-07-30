from __future__ import annotations

from django.db.models import Count, Exists, OuterRef, QuerySet

from apps.listings.selectors import public_listings

from .models import ListingReport, ListingReportState


def triage_queue() -> QuerySet[ListingReport]:
    return (
        ListingReport.objects.exclude(
            state__in=(ListingReportState.RESOLVED, ListingReportState.DISMISSED)
        )
        .annotate(listing_is_public=Exists(public_listings().filter(pk=OuterRef("listing_id"))))
        .select_related("listing__county", "listing__state", "assigned_to", "reporter")
        .prefetch_related("actions__actor")
        .order_by("created_at")
    )


def triage_metrics() -> dict[str, int]:
    counts = {
        row["state"]: row["count"]
        for row in ListingReport.objects.values("state").annotate(count=Count("id"))
    }
    return {
        "open": counts.get(ListingReportState.OPEN, 0),
        "acknowledged": counts.get(ListingReportState.ACKNOWLEDGED, 0),
        "escalated": counts.get(ListingReportState.ESCALATED, 0),
    }
