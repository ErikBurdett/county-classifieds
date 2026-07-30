from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog.models import (
    Category,
    ListingKind,
    ListingKindPriceMode,
    ListingPriceMode,
    ListingProduct,
    ListingProductUseCase,
    Vertical,
)
from apps.locations.models import County, State


class Command(BaseCommand):
    help = "Idempotently seed Texas, Potter/Randall, Autos taxonomy, and catalog examples."

    @transaction.atomic
    def handle(self, *_args: object, **_options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_texas_autos may only run with DEBUG enabled.")

        texas, _ = State.objects.update_or_create(
            fips="48",
            defaults={
                "usps_code": "TX",
                "name": "Texas",
                "slug": "texas",
                "is_active": True,
                "is_network_enabled": True,
            },
        )
        county_defaults = {"is_active": True, "is_network_enabled": True, "state": texas}
        for fips, name, slug in (
            ("48375", "Potter", "potter"),
            ("48381", "Randall", "randall"),
        ):
            County.objects.update_or_create(
                fips=fips,
                defaults={**county_defaults, "name": name, "slug": slug},
            )

        autos, _ = Vertical.objects.update_or_create(
            slug="autos",
            defaults={"name": "Autos", "display_order": 10, "is_active": True},
        )
        for display_order, name, slug in (
            (10, "Cars", "cars"),
            (20, "Trucks", "trucks"),
            (30, "SUVs", "suvs"),
            (40, "Vans", "vans"),
            (50, "Motorcycles", "motorcycles"),
            (60, "Other Autos", "other-autos"),
        ):
            Category.objects.update_or_create(
                vertical=autos,
                slug=slug,
                defaults={"name": name, "display_order": display_order, "is_active": True},
            )

        auto_listing, _ = ListingKind.objects.update_or_create(
            vertical=autos,
            name="Automobile",
            defaults={"is_active": True},
        )
        for price_mode in (
            ListingPriceMode.FIXED,
            ListingPriceMode.NEGOTIABLE,
            ListingPriceMode.CONTACT,
        ):
            ListingKindPriceMode.objects.get_or_create(
                listing_kind=auto_listing,
                price_mode=price_mode,
            )
        for product_code, price_mode in (
            ("AUTOS_NEW_FIXED", ListingPriceMode.FIXED),
            ("AUTOS_NEW_CONTACT", ListingPriceMode.CONTACT),
        ):
            ListingProduct.objects.update_or_create(
                product_code=product_code,
                defaults={
                    "listing_kind": auto_listing,
                    "use_case": ListingProductUseCase.NEW_LISTING,
                    "price_mode": price_mode,
                    "is_free": False,
                    "is_active": True,
                },
            )
        self.stdout.write(
            self.style.SUCCESS(
                "Seeded Texas, Potter/Randall, Autos categories, and catalog product examples."
            )
        )
