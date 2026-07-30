from __future__ import annotations

from django.contrib import admin

from .models import PolicyAcceptance, PolicyDocument


@admin.register(PolicyDocument)
class PolicyDocumentAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("kind", "version", "status", "requires_listing_acceptance", "updated_at")
    list_filter = ("kind", "status", "requires_listing_acceptance")
    readonly_fields = ("created_at", "updated_at", "activated_at")


@admin.register(PolicyAcceptance)
class PolicyAcceptanceAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("document", "user", "listing", "accepted_at")
    readonly_fields = ("document", "user", "listing", "accepted_at")
    search_fields = ("user__email", "listing__title")

    def has_add_permission(self, _request: object) -> bool:
        return False

    def has_change_permission(self, _request: object, _obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, _request: object, _obj: object | None = None) -> bool:
        return False
