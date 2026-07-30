from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from .models import (
    ListingKind,
    ListingKindPriceMode,
    ListingPriceMode,
    ListingProduct,
    ListingProductUseCase,
    ProductPrice,
)
from .selectors import effective_prices, eligible_products


class CatalogResolutionError(Exception):
    """Base class for fail-closed catalog resolution failures."""


class ProductNotEligibleError(CatalogResolutionError):
    """Raised when a product cannot be selected for the supplied listing context."""


class NoEffectivePriceError(CatalogResolutionError):
    """Raised when a product has no current server-owned price."""


class AmbiguousEffectivePriceError(CatalogResolutionError):
    """Raised when catalog data would yield more than one current price."""


@dataclass(frozen=True)
class ResolvedProductPrice:
    product: ListingProduct
    price: ProductPrice


@dataclass(frozen=True)
class ProductSelection:
    listing_kind: ListingKind
    product_code: str
    use_case: ListingProductUseCase
    price_mode: ListingPriceMode


def resolve_eligible_product(
    *,
    listing_kind: ListingKind,
    product_code: str,
    use_case: ListingProductUseCase,
    price_mode: ListingPriceMode,
) -> ListingProduct:
    """Resolve exactly one active product for a server-owned listing context."""
    if not listing_kind.is_active or not listing_kind.vertical.is_active:
        raise ProductNotEligibleError("The listing kind is inactive.")
    if not ListingKindPriceMode.objects.filter(
        listing_kind=listing_kind,
        price_mode=price_mode,
    ).exists():
        raise ProductNotEligibleError("The listing price mode is not supported.")

    product = (
        eligible_products(
            listing_kind=listing_kind,
            use_case=use_case,
            price_mode=price_mode,
        )
        .filter(product_code=product_code.upper())
        .first()
    )
    if product is None:
        raise ProductNotEligibleError("The product is not eligible for this listing.")
    return product


def resolve_current_price(
    *,
    product: ListingProduct,
    currency: str,
    at: datetime,
) -> ProductPrice:
    """Resolve one effective price, rejecting missing or corrupted price windows."""
    if timezone.is_naive(at):
        raise CatalogResolutionError("A timezone-aware timestamp is required.")
    if not product.is_active or product.listing_kind is None or not product.listing_kind.is_active:
        raise ProductNotEligibleError("The product is inactive.")

    prices = list(effective_prices(product=product, currency=currency, at=at)[:2])
    if not prices:
        raise NoEffectivePriceError("No effective price is available.")
    if len(prices) > 1:
        raise AmbiguousEffectivePriceError("More than one effective price is available.")
    return prices[0]


def resolve_eligible_product_price(
    *,
    selection: ProductSelection,
    currency: str,
    at: datetime,
) -> ResolvedProductPrice:
    """Resolve an eligible product and its single server-owned current price."""
    product = resolve_eligible_product(
        listing_kind=selection.listing_kind,
        product_code=selection.product_code,
        use_case=selection.use_case,
        price_mode=selection.price_mode,
    )
    price = resolve_current_price(product=product, currency=currency, at=at)
    return ResolvedProductPrice(product=product, price=price)
