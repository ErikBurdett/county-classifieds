from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.catalog.models import (
    ListingPriceMode,
    ListingProduct,
    ListingProductUseCase,
    ProductPrice,
)


class Command(BaseCommand):
    help = "Seed DEBUG-only generic listing distribution pricing for the local demo."

    def handle(self, *_args: Any, **_options: Any) -> None:
        if not settings.DEBUG:
            raise CommandError("Generic demo pricing may only be seeded with DEBUG=True.")
        now = timezone.now()
        for code, amount, description in (
            ("GENERIC_PRIMARY_PLACEMENT", 1000, "primary county"),
            ("GENERIC_ADDITIONAL_COUNTY", 500, "additional county"),
        ):
            product, _created = ListingProduct.objects.update_or_create(
                product_code=code,
                defaults={
                    "listing_kind": None,
                    "use_case": ListingProductUseCase.NEW_LISTING,
                    "price_mode": ListingPriceMode.FIXED,
                    "is_free": False,
                    "is_active": True,
                    "is_generic_distribution": True,
                    "duration_days": 30,
                },
            )
            if not ProductPrice.objects.filter(
                product=product, currency="USD", amount_minor=amount, effective_until__gt=now
            ).exists():
                ProductPrice.objects.create(
                    product=product,
                    currency="USD",
                    amount_minor=amount,
                    effective_from=now,
                    effective_until=now + timedelta(days=3650),
                )
            self.stdout.write(f"Configured {description}: {code}.")
