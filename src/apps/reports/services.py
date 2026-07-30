from __future__ import annotations

import hashlib
import hmac
import ipaddress
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.listings.selectors import public_listings

from .models import (
    ListingReport,
    ListingReportAction,
    ListingReportActionType,
    ListingReportReason,
    ListingReportState,
)

if TYPE_CHECKING:
    from apps.accounts.models import User


class ReportSubmissionSuppressedError(Exception):
    """Publicly indistinguishable rate-limit or duplicate suppression."""


@dataclass(frozen=True)
class ReportSubmission:
    listing_id: UUID
    reason: str
    description: str
    reporter_email: str
    source_ip: str
    reporter: User | None


def normalized_ip_hash(*, source_ip: str) -> str:
    """Return an HMAC of a canonical address; never persist the raw address."""
    try:
        normalized = ipaddress.ip_address(source_ip).compressed
    except ValueError:
        normalized = "invalid"
    return hmac.new(
        settings.REPORT_RATE_KEY_SECRET.encode(),
        normalized.encode(),
        hashlib.sha256,
    ).hexdigest()


def _fingerprint(*, listing_id: object, reason: str, description: str, source_ip_hash: str) -> str:
    normalized_description = " ".join(description.lower().split())
    payload = f"{listing_id}|{reason}|{normalized_description}|{source_ip_hash}"
    return hmac.new(
        settings.REPORT_RATE_KEY_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()


@transaction.atomic
def submit_listing_report(*, submission: ReportSubmission) -> ListingReport:
    """Create a durable report after enforcing public visibility and abuse limits."""
    # public_listings() outer-joins optional typed details for presentation;
    # PostgreSQL may lock only Listing for this transaction.
    listing = (
        public_listings().select_for_update(of=("self",)).filter(pk=submission.listing_id).first()
    )
    if listing is None:
        raise ReportSubmissionSuppressedError

    now = timezone.now()
    source_ip_hash = normalized_ip_hash(source_ip=submission.source_ip)
    fingerprint = _fingerprint(
        listing_id=listing.id,
        reason=submission.reason,
        description=submission.description,
        source_ip_hash=source_ip_hash,
    )
    since = now - timedelta(seconds=settings.REPORT_RATE_WINDOW_SECONDS)
    recent = ListingReport.objects.select_for_update().filter(created_at__gte=since)
    source_count = recent.filter(source_ip_hash=source_ip_hash).count()
    listing_count = recent.filter(listing=listing).count()
    user_count = (
        recent.filter(reporter=submission.reporter).count()
        if submission.reporter is not None
        else 0
    )
    duplicate = recent.filter(duplicate_fingerprint=fingerprint).exists()
    if (
        source_count >= settings.REPORT_RATE_SOURCE_LIMIT
        or listing_count >= settings.REPORT_RATE_LISTING_LIMIT
        or user_count >= settings.REPORT_RATE_USER_LIMIT
        or duplicate
    ):
        raise ReportSubmissionSuppressedError

    report = ListingReport.objects.create(
        listing=listing,
        reporter=submission.reporter,
        reporter_email=submission.reporter_email,
        reason=ListingReportReason(submission.reason),
        description=submission.description,
        source_ip_hash=source_ip_hash,
        duplicate_fingerprint=fingerprint,
    )
    ListingReportAction.objects.create(
        report=report,
        action_type=ListingReportActionType.SUBMITTED,
        from_state=ListingReportState.OPEN,
        to_state=ListingReportState.OPEN,
        actor=submission.reporter,
    )
    return report


_TRIAGE_TRANSITIONS = {
    "acknowledge": (ListingReportState.ACKNOWLEDGED, ListingReportActionType.ACKNOWLEDGED),
    "resolve": (ListingReportState.RESOLVED, ListingReportActionType.RESOLVED),
    "dismiss": (ListingReportState.DISMISSED, ListingReportActionType.DISMISSED),
    "escalate": (ListingReportState.ESCALATED, ListingReportActionType.ESCALATED),
}


@transaction.atomic
def transition_listing_report(
    *, report_id: UUID, actor: User, action: str, internal_note: str
) -> ListingReport:
    if not actor.has_perm("reports.triage_listingreport"):
        raise PermissionDenied
    try:
        to_state, action_type = _TRIAGE_TRANSITIONS[action]
    except KeyError as error:
        raise ValidationError("Invalid report action.") from error
    report = ListingReport.objects.select_for_update().get(pk=report_id)
    if report.state in {ListingReportState.RESOLVED, ListingReportState.DISMISSED}:
        raise ValidationError("Closed reports cannot be changed.")
    from_state = report.state
    report.state = to_state
    report.assigned_to = actor
    report.save(update_fields=("state", "assigned_to", "updated_at"))
    ListingReportAction.objects.create(
        report=report,
        action_type=action_type,
        from_state=from_state,
        to_state=to_state,
        actor=actor,
        assignee=actor,
        internal_note=internal_note,
    )
    return report
