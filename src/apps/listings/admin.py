from __future__ import annotations

from django.contrib import admin

from .models import (
    AutoDetails,
    Favorite,
    HomeGoodsDetails,
    Listing,
    ModerationAction,
    ModerationReasonCode,
)


class AutoDetailsInline(admin.StackedInline):  # type: ignore[type-arg]
    model = AutoDetails
    extra = 0
    max_num = 1


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("title", "seller", "category", "state", "county", "status", "updated_at")
    list_filter = ("status", "vertical", "category", "state")
    search_fields = ("title", "seller__display_name", "seller__user__email")
    readonly_fields = (
        "id",
        "status",
        "published_at",
        "expires_at",
        "last_material_edit_at",
        "lifecycle_revision",
        "created_at",
        "updated_at",
    )
    exclude = ("assigned_moderator",)
    inlines = (AutoDetailsInline,)


@admin.register(AutoDetails)
class AutoDetailsAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("listing", "year", "make", "model", "mileage", "title_status")
    list_filter = ("vehicle_type", "title_status")
    search_fields = ("make", "model", "listing__title")


@admin.register(HomeGoodsDetails)
class HomeGoodsDetailsAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("listing", "item_type", "brand", "condition", "working_status")
    list_filter = ("condition", "working_status", "fulfillment_preference")
    search_fields = ("item_type", "brand", "listing__title")


@admin.register(ModerationReasonCode)
class ModerationReasonCodeAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("code", "category", "version", "is_active", "requires_escalation")
    list_filter = ("is_active", "requires_escalation", "category")
    search_fields = ("code", "category", "seller_facing_text")


@admin.register(ModerationAction)
class ModerationActionAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("listing", "action_type", "from_status", "to_status", "actor", "created_at")
    list_filter = ("action_type", "to_status")
    search_fields = ("listing__title", "reason_code__code")
    readonly_fields = (
        "listing",
        "actor",
        "action_type",
        "from_status",
        "to_status",
        "reason_code",
        "internal_note",
        "seller_facing_note",
        "created_at",
    )

    def has_add_permission(self, _request: object) -> bool:
        return False

    def has_change_permission(self, _request: object, _obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, _request: object, _obj: object | None = None) -> bool:
        return False


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("user", "listing", "created_at")
    search_fields = ("user__email", "listing__title")
    readonly_fields = ("user", "listing", "created_at")

    def has_add_permission(self, _request: object) -> bool:
        return False

    def has_change_permission(self, _request: object, _obj: object | None = None) -> bool:
        return False

    def has_delete_permission(self, _request: object, _obj: object | None = None) -> bool:
        return False
