from __future__ import annotations

from datetime import datetime

from django.db.models import Exists, OuterRef, Q, QuerySet

from .models import (
    Category,
    ListingKind,
    ListingPriceMode,
    ListingProduct,
    ListingProductUseCase,
    ProductPrice,
    Vertical,
)


def active_postable_categories(*, vertical_id: int | None = None) -> QuerySet[Category]:
    """Return active leaves, treating parents without active children as leaves."""
    active_children = Category.objects.filter(parent_id=OuterRef("pk"), is_active=True)
    categories = Category.objects.filter(
        is_active=True,
        vertical__is_active=True,
    ).annotate(has_active_children=Exists(active_children))
    if vertical_id is not None:
        categories = categories.filter(vertical_id=vertical_id)
    return categories.filter(has_active_children=False).select_related("vertical", "parent")


def automatic_primary_category(*, vertical: Vertical) -> Category | None:
    """Return the seed-owned invisible primary leaf for special overflow workflows."""
    if vertical.slug != "others":
        return None
    return active_postable_categories(vertical_id=vertical.id).filter(slug="general").first()


def category_hierarchy_label(*, category: Category) -> str:
    """Return a disambiguated vertical/group/leaf category label."""
    hierarchy = [category.vertical.name]
    parent = category.parent
    if parent is not None:
        hierarchy.append(parent.name)
    hierarchy.append(category.name)
    return " \u203a ".join(hierarchy)


def eligible_products(
    *,
    listing_kind: ListingKind,
    use_case: ListingProductUseCase,
    price_mode: ListingPriceMode,
) -> QuerySet[ListingProduct]:
    """Return active catalog products eligible for a listing selection."""
    return (
        ListingProduct.objects.filter(
            listing_kind=listing_kind,
            use_case=use_case,
            price_mode=price_mode,
            is_active=True,
            listing_kind__is_active=True,
            listing_kind__vertical__is_active=True,
        )
        .select_related("listing_kind__vertical")
        .order_by("product_code")
    )


def effective_prices(
    *,
    product: ListingProduct,
    currency: str,
    at: datetime,
) -> QuerySet[ProductPrice]:
    """Return all price rows effective at an aware timestamp."""
    return ProductPrice.objects.filter(
        product=product,
        currency=currency.upper(),
        effective_from__lte=at,
    ).filter(Q(effective_until__isnull=True) | Q(effective_until__gt=at))
