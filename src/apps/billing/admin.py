from __future__ import annotations

from django.contrib import admin

from .models import FeaturedPlacement, Order, OrderLine, PaymentEvent


class OrderLineInline(admin.TabularInline):  # type: ignore[type-arg]
    model = OrderLine
    extra = 0
    readonly_fields = (
        "id",
        "product",
        "product_code",
        "description",
        "unit_amount_minor",
        "quantity",
        "currency",
        "duration_days",
        "created_at",
    )
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = (
        "id",
        "listing",
        "seller",
        "total_minor",
        "currency",
        "status",
        "paid_at",
        "created_at",
    )
    list_filter = ("status", "provider", "currency")
    search_fields = ("id", "provider_reference", "listing__title", "seller__display_name")
    readonly_fields = (
        "id",
        "listing",
        "seller",
        "currency",
        "total_minor",
        "provider",
        "provider_reference",
        "status",
        "paid_at",
        "created_at",
        "updated_at",
    )
    inlines = (OrderLineInline,)

    def has_add_permission(self, _request: object) -> bool:
        return False

    def has_change_permission(self, _request: object, _obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, _request: object, _obj: object | None = None) -> bool:
        return False


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("provider", "provider_event_id", "event_type", "order", "status", "occurred_at")
    list_filter = ("provider", "event_type", "status")
    readonly_fields = (
        "id",
        "provider",
        "provider_event_id",
        "event_type",
        "order",
        "amount_minor",
        "currency",
        "occurred_at",
        "status",
        "processed_at",
        "failure_reason",
        "created_at",
    )

    def has_add_permission(self, _request: object) -> bool:
        return False

    def has_change_permission(self, _request: object, _obj: object | None = None) -> bool:
        return False


@admin.register(FeaturedPlacement)
class FeaturedPlacementAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("listing", "starts_at", "ends_at", "created_at")
    readonly_fields = ("id", "listing", "order_line", "starts_at", "ends_at", "created_at")
