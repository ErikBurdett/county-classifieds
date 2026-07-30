from __future__ import annotations

import uuid
from typing import Never

from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.db import models


class ListingReportReason(models.TextChoices):
    SCAM = "scam", "Scam or fraud"
    PROHIBITED = "prohibited", "Prohibited item or service"
    STOLEN_OR_COUNTERFEIT = "stolen_counterfeit", "Suspected stolen or counterfeit item"
    INACCURATE = "inaccurate", "Inaccurate or misleading"
    ABUSE_OR_OTHER = "abuse_other", "Abuse or other concern"


class ListingReportState(models.TextChoices):
    OPEN = "open", "Open"
    ACKNOWLEDGED = "acknowledged", "Acknowledged"
    RESOLVED = "resolved", "Resolved"
    DISMISSED = "dismissed", "Dismissed"
    ESCALATED = "escalated", "Escalated"


class ListingReportActionType(models.TextChoices):
    SUBMITTED = "submitted", "Submitted"
    ACKNOWLEDGED = "acknowledged", "Acknowledged"
    RESOLVED = "resolved", "Resolved"
    DISMISSED = "dismissed", "Dismissed"
    ESCALATED = "escalated", "Escalated"


class ListingReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.PROTECT, related_name="reports"
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="listing_reports",
    )
    reporter_email = models.EmailField(blank=True)
    reason = models.CharField(max_length=32, choices=ListingReportReason.choices, db_index=True)
    description = models.TextField(blank=True, validators=[MaxLengthValidator(2000)])
    source_ip_hash = models.CharField(max_length=64, db_index=True)
    duplicate_fingerprint = models.CharField(max_length=64, db_index=True)
    state = models.CharField(
        max_length=16,
        choices=ListingReportState.choices,
        default=ListingReportState.OPEN,
        db_index=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_listing_reports",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [("triage_listingreport", "Can triage listing reports")]
        indexes = [
            models.Index(fields=("state", "created_at"), name="reports_state_created"),
            models.Index(fields=("listing", "created_at"), name="reports_listing_created"),
            models.Index(fields=("reporter", "created_at"), name="reports_reporter_created"),
        ]

    def __str__(self) -> str:
        return f"Report {self.id} for {self.listing_id}"


class ListingReportAction(models.Model):
    """Append-only staff and system audit history for a listing report."""

    report = models.ForeignKey(ListingReport, on_delete=models.PROTECT, related_name="actions")
    action_type = models.CharField(max_length=16, choices=ListingReportActionType.choices)
    from_state = models.CharField(max_length=16, choices=ListingReportState.choices)
    to_state = models.CharField(max_length=16, choices=ListingReportState.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="listing_report_actions",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="listing_report_action_assignments",
    )
    internal_note = models.TextField(blank=True, validators=[MaxLengthValidator(2000)])
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=("report", "created_at"), name="reports_action_report_at")]

    def __str__(self) -> str:
        return f"{self.action_type} report action"

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding:
            raise ValueError("Listing report actions are immutable.")
        super().save(*args, **kwargs)  # type: ignore[arg-type]

    def delete(self, *_args: object, **_kwargs: object) -> Never:
        raise ValueError("Listing report actions are immutable.")
