from __future__ import annotations

from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import SellerProfile
from apps.catalog.models import Category
from apps.listings.models import Listing
from apps.listings.services import (
    create_ag_equipment_draft,
    create_livestock_draft,
    create_pasture_draft,
)
from apps.locations.models import County, State

DEMO_EMAILS = (
    "telephoneheater@local.test",
    "albuquerque@local.test",
    "denver@local.test",
    "tulsa@local.test",
)
REQUIRED_DEMO_PROFILES = 2


class Command(BaseCommand):
    help = "Seed bounded private rural drafts for existing local demo accounts; DEBUG only."

    @transaction.atomic
    def handle(self, *_args: object, **_options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_demo_rural_drafts may only run with DEBUG enabled.")
        profiles = list(
            SellerProfile.objects.filter(user__email__in=DEMO_EMAILS)
            .select_related("user")
            .order_by("user__email")[:REQUIRED_DEMO_PROFILES]
        )
        if len(profiles) < REQUIRED_DEMO_PROFILES:
            raise CommandError(
                "seed_demo_rural_drafts requires at least two existing local demo seller accounts."
            )
        state = State.objects.filter(is_active=True).order_by("name").first()
        if state is None:
            raise CommandError("seed_demo_rural_drafts requires an active state and county.")
        county = County.objects.filter(state=state, is_active=True).order_by("name").first()
        if county is None:
            raise CommandError("seed_demo_rural_drafts requires an active state and county.")
        ag_category = Category.objects.filter(
            vertical__slug="farm-ranch", slug="farm-equipment", is_active=True
        ).first()
        livestock_category = Category.objects.filter(
            vertical__slug="livestock-animals", slug="livestock", is_active=True
        ).first()
        pasture_category = Category.objects.filter(
            vertical__slug="farm-ranch", slug="land-pasture", is_active=True
        ).first()
        if ag_category is None or livestock_category is None or pasture_category is None:
            raise CommandError(
                "seed_demo_rural_drafts requires Farm & Ranch and Livestock catalog categories."
            )

        common_values = {
            "state": state,
            "county": county,
            "city": county.name,
            "currency": "USD",
        }
        ag_title = "Demo private tractor draft"
        if not Listing.objects.filter(seller=profiles[0], title=ag_title).exists():
            create_ag_equipment_draft(
                seller=profiles[0],
                listing_values={
                    **common_values,
                    "category": ag_category,
                    "title": ag_title,
                    "description": "Local-only private agricultural equipment draft.",
                    "price_minor": 450000,
                },
                ag_equipment_values={
                    "equipment_type": "tractor",
                    "make": "Demo",
                    "model": "Field 50",
                    "year": 2016,
                    "hours": 1200,
                    "powered": True,
                    "condition": "used",
                },
            )

        livestock_title = "Demo private cattle draft"
        if not Listing.objects.filter(seller=profiles[1], title=livestock_title).exists():
            create_livestock_draft(
                seller=profiles[1],
                listing_values={
                    **common_values,
                    "category": livestock_category,
                    "title": livestock_title,
                    "description": "Local-only private livestock draft.",
                    "price_minor": 150000,
                },
                livestock_values={
                    "species": "cattle",
                    "breed": "Mixed",
                    "animal_class": "Cow-calf pair",
                    "head_count": 4,
                    "age_or_weight": "Mature",
                    "sale_unit": "head",
                },
            )

        pasture_title = "Demo private pasture draft"
        if not Listing.objects.filter(seller=profiles[0], title=pasture_title).exists():
            create_pasture_draft(
                seller=profiles[0],
                listing_values={
                    **common_values,
                    "category": pasture_category,
                    "title": pasture_title,
                    "description": "Local-only private pasture draft.",
                    "price_minor": 200000,
                },
                pasture_values={
                    "acreage": "40.00",
                    "water_available": True,
                    "fenced": True,
                    "lease_term": "Annual lease",
                    "use_restrictions": "Grazing use only.",
                    "available_date": date(2026, 9, 1),
                },
            )
        self.stdout.write(self.style.SUCCESS("Seeded bounded private rural demo drafts."))
