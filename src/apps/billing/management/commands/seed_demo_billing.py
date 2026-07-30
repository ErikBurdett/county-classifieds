from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
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


class Command(BaseCommand):
    help = "Seed the DEBUG-only $10.00, 30-day local Autos billing demonstration."

    @transaction.atomic
    def handle(self, *_args: object, **_options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_demo_billing may only run with DEBUG enabled.")
        autos = Vertical.objects.filter(slug="autos", is_active=True).first()
        if autos is None:
            raise CommandError("Seed the Autos catalog before seeding local demo billing.")
        listing_kind = ListingKind.objects.filter(
            vertical=autos, name="Automobile", is_active=True
        ).first()
        if listing_kind is None:
            raise CommandError("The active Autos Automobile listing kind is required.")
        if not ListingKindPriceMode.objects.filter(
            listing_kind=listing_kind, price_mode=ListingPriceMode.FIXED
        ).exists():
            raise CommandError("The Autos Automobile kind must support fixed price.")
        product, _ = ListingProduct.objects.update_or_create(
            product_code="AUTOS_NEW_FIXED",
            defaults={
                "listing_kind": listing_kind,
                "use_case": ListingProductUseCase.NEW_LISTING,
                "price_mode": ListingPriceMode.FIXED,
                "is_free": False,
                "is_active": True,
                "duration_days": 30,
            },
        )
        if not ProductPrice.objects.filter(
            product=product,
            currency="USD",
            amount_minor=1000,
            effective_until__isnull=True,
        ).exists():
            ProductPrice.objects.create(
                product=product,
                currency="USD",
                amount_minor=1000,
                effective_from=timezone.now(),
            )
        self.stdout.write(
            self.style.SUCCESS(
                "Seeded local demo billing: AUTOS_NEW_FIXED at $10.00 USD for 30 days. "
                "This is not production pricing policy."
            )
        )
