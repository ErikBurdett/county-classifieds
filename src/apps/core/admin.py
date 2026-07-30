from __future__ import annotations

from django.contrib import admin

from .models import OutboxDeliveryAttempt, OutboxEvent


@admin.register(OutboxEvent)
class OutboxEventAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = (
        "event_type",
        "aggregate_type",
        "aggregate_reference",
        "available_at",
        "attempt_count",
        "locked_at",
        "processed_at",
        "failed_at",
    )
    list_filter = ("event_type", "processed_at", "failed_at")
    search_fields = ("idempotency_key", "aggregate_reference")
    readonly_fields = (
        "id",
        "event_type",
        "payload",
        "aggregate_type",
        "aggregate_reference",
        "available_at",
        "locked_at",
        "locked_by",
        "processed_at",
        "failed_at",
        "attempt_count",
        "idempotency_key",
        "last_error",
        "created_at",
    )
    ordering = ("available_at",)

    def has_add_permission(self, _request: object) -> bool:
        return False

    def has_change_permission(self, _request: object, _obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, _request: object, _obj: object | None = None) -> bool:
        return False


@admin.register(OutboxDeliveryAttempt)
class OutboxDeliveryAttemptAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("event", "attempt_number", "started_at", "finished_at", "succeeded")
    list_filter = ("succeeded",)
    readonly_fields = (
        "event",
        "attempt_number",
        "started_at",
        "finished_at",
        "succeeded",
        "error_message",
    )

    def has_add_permission(self, _request: object) -> bool:
        return False

    def has_change_permission(self, _request: object, _obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, _request: object, _obj: object | None = None) -> bool:
        return False
