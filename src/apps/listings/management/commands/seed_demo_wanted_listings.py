from __future__ import annotations

from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import SellerProfile
from apps.catalog.models import Category
from apps.listings.models import Listing
from apps.listings.services import create_wanted_draft, publish_demo_listing
from apps.locations.models import County, ZipCountyReference


class Command(BaseCommand):
    help = "Seed synthetic wanted demos through normal listing services; DEBUG only."

    def handle(self, *_args: object, **_options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_demo_wanted_listings may only run with DEBUG enabled.")
        seller = SellerProfile.objects.order_by("id").first()
        if seller is None:
            raise CommandError("A local demo seller is required; run seed-demo-minimal first.")
        counties = list(
            County.objects.filter(
                is_active=True,
                is_network_enabled=True,
                state__is_active=True,
                state__is_network_enabled=True,
            )
            .select_related("state")
            .order_by("fips")[:3]
        )
        categories = list(
            Category.objects.filter(is_active=True, vertical__is_active=True)
            .exclude(children__is_active=True)
            .select_related("vertical")
            .order_by("vertical__display_order", "display_order")[:3]
        )
        if len(counties) < 1 or len(categories) < 1:
            raise CommandError("Active local locations and postable catalog leaves are required.")
        created = unchanged = 0
        for index, category in enumerate(categories):
            county = counties[index % len(counties)]
            title = f"Synthetic wanted fixture: {category.name}"
            listing = Listing.objects.filter(title=title, intent="wanted").first()
            if listing is None:
                postal_code = county.fips
                ZipCountyReference.objects.get_or_create(
                    postal_code=postal_code,
                    county=county,
                    defaults={
                        "source_name": "Local wanted fixture",
                        "source_url": "https://local.test/wanted",
                        "release_version": "2026-07-31",
                        "release_date": date(2026, 7, 31),
                        "sha256_checksum": "0" * 64,
                        "transformation_version": "local-demo-v1",
                    },
                )
                listing = create_wanted_draft(
                    seller=seller,
                    listing_values={
                        "category": category,
                        "state": county.state,
                        "county": county,
                        "city": county.name,
                        "title": title,
                        "description": "Synthetic local demonstration request; not a real request.",
                    },
                    generic_values={
                        "price_mode": "contact",
                        "postal_code": postal_code,
                        "street_address": "",
                    },
                    additional_counties=[],
                    controlled_categories=[],
                    seller_tags=[],
                    custom_fields=[],
                )
                publish_demo_listing(listing_id=listing.id)
                created += 1
            else:
                unchanged += 1
        self.stdout.write(
            self.style.SUCCESS(f"Wanted demo inventory: {created} created, {unchanged} unchanged.")
        )
