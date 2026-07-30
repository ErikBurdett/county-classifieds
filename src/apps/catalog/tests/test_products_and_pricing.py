from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.utils import timezone

from apps.catalog.models import (
    ListingKind,
    ListingKindPriceMode,
    ListingPriceMode,
    ListingProduct,
    ListingProductUseCase,
    ProductPrice,
    Vertical,
)
from apps.catalog.services import (
    AmbiguousEffectivePriceError,
    CatalogResolutionError,
    NoEffectivePriceError,
    ProductNotEligibleError,
    ProductSelection,
    resolve_current_price,
    resolve_eligible_product_price,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def autos_kind() -> ListingKind:
    autos = Vertical.objects.create(name="Autos", slug="autos")
    kind = ListingKind.objects.create(vertical=autos, name="Automobile")
    for price_mode in (
        ListingPriceMode.FIXED,
        ListingPriceMode.NEGOTIABLE,
        ListingPriceMode.CONTACT,
    ):
        ListingKindPriceMode.objects.create(listing_kind=kind, price_mode=price_mode)
    return kind


@pytest.fixture
def fixed_product(autos_kind: ListingKind) -> ListingProduct:
    return ListingProduct.objects.create(
        listing_kind=autos_kind,
        product_code="AUTOS_NEW_FIXED",
        use_case=ListingProductUseCase.NEW_LISTING,
        price_mode=ListingPriceMode.FIXED,
    )


def test_resolves_eligible_product_and_current_price(
    autos_kind: ListingKind, fixed_product: ListingProduct
) -> None:
    now = timezone.now()
    price = ProductPrice.objects.create(
        product=fixed_product,
        currency="USD",
        amount_minor=2500,
        effective_from=now - timedelta(minutes=1),
    )

    resolved = resolve_eligible_product_price(
        selection=ProductSelection(
            listing_kind=autos_kind,
            product_code="autos_new_fixed",
            use_case=ListingProductUseCase.NEW_LISTING,
            price_mode=ListingPriceMode.FIXED,
        ),
        currency="usd",
        at=now,
    )

    assert resolved.product == fixed_product
    assert resolved.price == price


def test_product_validation_rejects_unsupported_price_mode(autos_kind: ListingKind) -> None:
    product = ListingProduct(
        listing_kind=autos_kind,
        product_code="AUTOS_NEW_FREE",
        use_case=ListingProductUseCase.NEW_LISTING,
        price_mode=ListingPriceMode.FREE,
        is_free=True,
    )

    with pytest.raises(ValidationError, match="not supported"):
        product.full_clean()


def test_product_validation_rejects_free_autos_product(autos_kind: ListingKind) -> None:
    ListingKindPriceMode.objects.create(listing_kind=autos_kind, price_mode=ListingPriceMode.FREE)
    product = ListingProduct(
        listing_kind=autos_kind,
        product_code="AUTOS_NEW_FREE",
        use_case=ListingProductUseCase.NEW_LISTING,
        price_mode=ListingPriceMode.FREE,
        is_free=True,
    )

    with pytest.raises(ValidationError, match="cannot be free"):
        product.full_clean()


def test_price_validation_requires_positive_price_for_non_free_product(
    fixed_product: ListingProduct,
) -> None:
    price = ProductPrice(
        product=fixed_product,
        currency="USD",
        amount_minor=0,
        effective_from=timezone.now(),
    )

    with pytest.raises(ValidationError, match="Only free products"):
        price.full_clean()


def test_resolver_fails_closed_for_inactive_kind(
    autos_kind: ListingKind, fixed_product: ListingProduct
) -> None:
    now = timezone.now()
    ProductPrice.objects.create(
        product=fixed_product,
        currency="USD",
        amount_minor=2500,
        effective_from=now - timedelta(minutes=1),
    )
    autos_kind.is_active = False
    autos_kind.save(update_fields=("is_active",))

    with pytest.raises(ProductNotEligibleError, match="inactive"):
        resolve_eligible_product_price(
            selection=ProductSelection(
                listing_kind=autos_kind,
                product_code=fixed_product.product_code,
                use_case=ListingProductUseCase.NEW_LISTING,
                price_mode=ListingPriceMode.FIXED,
            ),
            currency="USD",
            at=now,
        )


def test_resolver_fails_closed_for_inactive_product(fixed_product: ListingProduct) -> None:
    now = timezone.now()
    ProductPrice.objects.create(
        product=fixed_product,
        currency="USD",
        amount_minor=2500,
        effective_from=now - timedelta(minutes=1),
    )
    fixed_product.is_active = False
    fixed_product.save(update_fields=("is_active",))

    with pytest.raises(ProductNotEligibleError, match="inactive"):
        resolve_current_price(product=fixed_product, currency="USD", at=now)


def test_resolver_fails_closed_for_unsupported_price_mode(
    autos_kind: ListingKind, fixed_product: ListingProduct
) -> None:
    with pytest.raises(ProductNotEligibleError, match="not supported"):
        resolve_eligible_product_price(
            selection=ProductSelection(
                listing_kind=autos_kind,
                product_code=fixed_product.product_code,
                use_case=ListingProductUseCase.NEW_LISTING,
                price_mode=ListingPriceMode.FREE,
            ),
            currency="USD",
            at=timezone.now(),
        )


def test_resolver_fails_closed_without_effective_price(
    autos_kind: ListingKind, fixed_product: ListingProduct
) -> None:
    with pytest.raises(NoEffectivePriceError, match="No effective"):
        resolve_eligible_product_price(
            selection=ProductSelection(
                listing_kind=autos_kind,
                product_code=fixed_product.product_code,
                use_case=ListingProductUseCase.NEW_LISTING,
                price_mode=ListingPriceMode.FIXED,
            ),
            currency="USD",
            at=timezone.now(),
        )


def test_resolver_rejects_naive_timestamp(fixed_product: ListingProduct) -> None:
    with pytest.raises(CatalogResolutionError, match="timezone-aware"):
        resolve_current_price(
            product=fixed_product,
            currency="USD",
            at=datetime(2026, 7, 23, 12, 0),
        )


def test_resolver_fails_closed_for_ambiguous_effective_price(
    fixed_product: ListingProduct, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = timezone.now()
    price = ProductPrice.objects.create(
        product=fixed_product,
        currency="USD",
        amount_minor=2500,
        effective_from=now - timedelta(minutes=1),
    )
    monkeypatch.setattr(
        "apps.catalog.services.effective_prices",
        lambda **_kwargs: [price, price],
    )

    with pytest.raises(AmbiguousEffectivePriceError, match="More than one"):
        resolve_current_price(product=fixed_product, currency="USD", at=now)


@pytest.mark.skipif(connection.vendor != "postgresql", reason="PostgreSQL exclusion constraint")
def test_postgresql_rejects_overlapping_product_prices(fixed_product: ListingProduct) -> None:
    now = timezone.now()
    ProductPrice.objects.create(
        product=fixed_product,
        currency="USD",
        amount_minor=2500,
        effective_from=now - timedelta(hours=1),
        effective_until=now + timedelta(hours=1),
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        ProductPrice.objects.create(
            product=fixed_product,
            currency="USD",
            amount_minor=3000,
            effective_from=now,
            effective_until=now + timedelta(hours=1),
        )


@pytest.mark.skipif(connection.vendor != "postgresql", reason="PostgreSQL integrity trigger")
def test_postgresql_rejects_zero_price_for_non_free_product(fixed_product: ListingProduct) -> None:
    with pytest.raises(DatabaseError), transaction.atomic():
        ProductPrice.objects.create(
            product=fixed_product,
            currency="USD",
            amount_minor=0,
            effective_from=timezone.now(),
        )
