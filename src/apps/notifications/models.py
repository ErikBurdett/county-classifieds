from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from .destinations import resolve_destination


class UserNotification(models.Model):
    """A durable, recipient-owned in-app notification."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    event_type = models.CharField(max_length=96)
    title = models.CharField(max_length=160)
    body = models.CharField(max_length=500)
    destination_route = models.CharField(max_length=96, blank=True)
    destination_kwargs = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=200, unique=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=("recipient", "read_at", "-created_at"),
                name="notify_recipient_read_idx",
            ),
            models.Index(
                fields=("recipient", "-created_at"),
                name="notify_recipient_created_idx",
            ),
            models.Index(
                fields=("event_type", "-created_at"),
                name="notify_type_created_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} for {self.recipient_id}"

    @property
    def destination_url(self) -> str | None:
        if not isinstance(self.destination_kwargs, dict):
            return None
        try:
            return resolve_destination(
                route_name=self.destination_route,
                route_kwargs=self.destination_kwargs,
            )
        except ValueError:
            return None
