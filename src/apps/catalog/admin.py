from __future__ import annotations

from django.contrib import admin

from .models import (
    Category,
    ListingKind,
    ListingKindPriceMode,
    ListingProduct,
    ProductPrice,
    Vertical,
)


@admin.register(Vertical)
class VerticalAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("name", "slug", "display_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    ordering = ("display_order", "name")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("name", "vertical", "parent", "display_order", "is_active")
    list_filter = ("vertical", "is_active")
    search_fields = ("name", "slug", "vertical__name", "vertical__slug", "parent__name")
    ordering = ("vertical__display_order", "display_order", "name")
    list_select_related = ("vertical", "parent")


@admin.register(ListingKind)
class ListingKindAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("name", "vertical", "is_active")
    list_filter = ("vertical", "is_active")
    search_fields = ("name", "vertical__name", "vertical__slug")

    def has_delete_permission(self, _request: object, _obj: object | None = None) -> bool:
        return False


@admin.register(ListingKindPriceMode)
class ListingKindPriceModeAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("listing_kind", "price_mode")
    list_filter = ("price_mode", "listing_kind__vertical")
    search_fields = ("listing_kind__name", "listing_kind__vertical__name")

    def has_delete_permission(self, _request: object, _obj: object | None = None) -> bool:
        return False


@admin.register(ListingProduct)
class ListingProductAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = (
        "product_code",
        "listing_kind",
        "use_case",
        "price_mode",
        "is_free",
        "is_active",
    )
    list_filter = ("is_active", "is_free", "use_case", "price_mode", "listing_kind__vertical")
    search_fields = ("product_code", "listing_kind__name", "listing_kind__vertical__name")

    def get_readonly_fields(
        self, _request: object, obj: ListingProduct | None = None
    ) -> tuple[str, ...]:
        if obj is not None:
            return ("product_code",)
        return ()

    def has_delete_permission(self, _request: object, _obj: object | None = None) -> bool:
        return False


@admin.register(ProductPrice)
class ProductPriceAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("product", "currency", "amount_minor", "effective_from", "effective_until")
    list_filter = ("currency", "product__listing_kind__vertical")
    search_fields = ("product__product_code",)
    date_hierarchy = "effective_from"

    def get_readonly_fields(
        self, _request: object, obj: ProductPrice | None = None
    ) -> tuple[str, ...]:
        if obj is not None:
            return ("product", "currency", "amount_minor", "effective_from", "effective_until")
        return ()

    def has_delete_permission(self, _request: object, _obj: object | None = None) -> bool:
        return False
