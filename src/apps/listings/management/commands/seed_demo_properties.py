from __future__ import annotations

from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import SellerProfile
from apps.catalog.models import Category
from apps.listings.models import Listing
from apps.listings.services import create_home_draft, create_rental_draft
from apps.locations.models import County, State

DEMO_EMAILS = (
    "telephoneheater@local.test",
    "albuquerque@local.test",
    "denver@local.test",
    "tulsa@local.test",
)
REQUIRED_DEMO_PROFILES = 2


class Command(BaseCommand):
    help = "Seed bounded private property drafts for existing local demo accounts; DEBUG only."

    @transaction.atomic
    def handle(self, *_args: object, **_options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_demo_properties may only run with DEBUG enabled.")
        profiles = list(
            SellerProfile.objects.filter(user__email__in=DEMO_EMAILS)
            .select_related("user")
            .order_by("user__email")[:REQUIRED_DEMO_PROFILES]
        )
        if len(profiles) < REQUIRED_DEMO_PROFILES:
            raise CommandError(
                "seed_demo_properties requires at least two existing local demo seller accounts."
            )
        state = State.objects.filter(is_active=True).order_by("name").first()
        if state is None:
            raise CommandError("seed_demo_properties requires an active state and county.")
        county = County.objects.filter(state=state, is_active=True).order_by("name").first()
        if county is None:
            raise CommandError("seed_demo_properties requires an active state and county.")
        home_category = Category.objects.filter(
            vertical__slug="real-estate", slug="homes-for-sale", is_active=True
        ).first()
        rental_category = Category.objects.filter(
            vertical__slug="rentals", slug="homes-for-rent", is_active=True
        ).first()
        if home_category is None or rental_category is None:
            raise CommandError(
                "seed_demo_properties requires the Homes and Rentals catalog categories."
            )

        home_title = "Demo private home draft"
        if not Listing.objects.filter(seller=profiles[0], title=home_title).exists():
            create_home_draft(
                seller=profiles[0],
                listing_values={
                    "category": home_category,
                    "state": state,
                    "county": county,
                    "city": county.name,
                    "title": home_title,
                    "description": "Local-only private property draft.",
                    "price_minor": 25000000,
                    "currency": "USD",
                },
                home_values={
                    "property_type": "house",
                    "beds": 3,
                    "baths": "2.0",
                    "square_feet": 1800,
                    "year_built": 2005,
                    "lot_size": "0.20",
                    "lot_size_unit": "acres",
                    "street_address": "100 Demo Lane",
                    "address_line_2": "",
                    "postal_code": "00000",
                    "general_area": f"Near {county.name}",
                    "exact_address_public": False,
                },
            )

        rental_title = "Demo private rental draft"
        if not Listing.objects.filter(seller=profiles[1], title=rental_title).exists():
            create_rental_draft(
                seller=profiles[1],
                listing_values={
                    "category": rental_category,
                    "state": state,
                    "county": county,
                    "city": county.name,
                    "title": rental_title,
                    "description": "Local-only private rental draft.",
                    "price_minor": 0,
                    "currency": "USD",
                },
                rental_values={
                    "rental_type": "apartment",
                    "monthly_rent_minor": 125000,
                    "security_deposit_minor": 125000,
                    "beds": 2,
                    "baths": "1.0",
                    "available_date": date(2026, 8, 1),
                    "pets_policy": "case_by_case",
                    "lease_term_months": 12,
                    "flexible_term": False,
                    "street_address": "200 Demo Lane",
                    "address_line_2": "",
                    "postal_code": "00000",
                    "general_area": f"Near {county.name}",
                    "exact_address_public": False,
                },
            )
        self.stdout.write(self.style.SUCCESS("Seeded bounded private demo property drafts."))
