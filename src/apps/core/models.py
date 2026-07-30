from __future__ import annotations

import uuid

from django.db import models


class OutboxEvent(models.Model):
    """A durable, transport-neutral side effect recorded with domain state."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=96)
    payload = models.JSONField(default=dict)
    aggregate_type = models.CharField(max_length=96)
    aggregate_reference = models.CharField(max_length=128)
    available_at = models.DateTimeField()
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.CharField(max_length=64, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    idempotency_key = models.CharField(max_length=200, unique=True)
    last_error = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=("processed_at", "failed_at", "available_at"),
                name="core_outbox_ready_idx",
            ),
            models.Index(fields=("locked_at",), name="core_outbox_lease_idx"),
            models.Index(fields=("event_type", "created_at"), name="core_outbox_type_idx"),
        ]
        ordering = ("available_at", "created_at")

    def __str__(self) -> str:
        return f"{self.event_type}:{self.aggregate_reference}"


class OutboxDeliveryAttempt(models.Model):
    """Append-only record of a claimed event delivery attempt."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        OutboxEvent, on_delete=models.PROTECT, related_name="delivery_attempts"
    )
    attempt_number = models.PositiveSmallIntegerField()
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    succeeded = models.BooleanField(default=False)
    error_message = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("event", "attempt_number"), name="core_outbox_attempt_unique"
            )
        ]
        indexes = [models.Index(fields=("event", "-started_at"), name="core_attempt_event_idx")]
        ordering = ("-started_at",)

    def __str__(self) -> str:
        return f"{self.event_id} attempt {self.attempt_number}"
