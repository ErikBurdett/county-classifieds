from __future__ import annotations

from django.contrib import admin

from .models import ListingReport, ListingReportAction


@admin.register(ListingReport)
class ListingReportAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("id", "listing", "reason", "state", "assigned_to", "created_at")
    list_filter = ("reason", "state")
    search_fields = ("listing__title", "reporter_email")
    readonly_fields = (
        "id",
        "listing",
        "reporter",
        "reporter_email",
        "reason",
        "description",
        "source_ip_hash",
        "duplicate_fingerprint",
        "state",
        "assigned_to",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, _request: object) -> bool:
        return False

    def has_change_permission(self, _request: object, _obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, _request: object, _obj: object | None = None) -> bool:
        return False


@admin.register(ListingReportAction)
class ListingReportActionAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("report", "action_type", "actor", "assignee", "created_at")
    list_filter = ("action_type",)
    search_fields = ("report__listing__title", "internal_note")
    readonly_fields = (
        "report",
        "action_type",
        "from_state",
        "to_state",
        "actor",
        "assignee",
        "internal_note",
        "created_at",
    )

    def has_add_permission(self, _request: object) -> bool:
        return False

    def has_change_permission(self, _request: object, _obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, _request: object, _obj: object | None = None) -> bool:
        return False
