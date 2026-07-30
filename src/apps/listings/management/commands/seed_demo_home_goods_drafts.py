from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import SellerProfile
from apps.catalog.models import Category
from apps.listings.models import Listing
from apps.listings.services import create_appliances_draft, create_home_garden_draft
from apps.locations.models import County, State

DEMO_EMAILS = (
    "telephoneheater@local.test",
    "albuquerque@local.test",
    "denver@local.test",
    "tulsa@local.test",
)
REQUIRED_DEMO_PROFILES = 2


class Command(BaseCommand):
    help = "Seed bounded private Home Goods drafts for existing local demo accounts; DEBUG only."

    @transaction.atomic
    def handle(self, *_args: object, **_options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_demo_home_goods_drafts may only run with DEBUG enabled.")
        profiles = list(
            SellerProfile.objects.filter(user__email__in=DEMO_EMAILS)
            .select_related("user")
            .order_by("user__email")[:REQUIRED_DEMO_PROFILES]
        )
        if len(profiles) < REQUIRED_DEMO_PROFILES:
            raise CommandError(
                "seed_demo_home_goods_drafts requires at least two existing local "
                "demo seller accounts."
            )
        state = State.objects.filter(is_active=True).order_by("name").first()
        if state is None:
            raise CommandError("seed_demo_home_goods_drafts requires an active state and county.")
        county = County.objects.filter(state=state, is_active=True).order_by("name").first()
        if county is None:
            raise CommandError("seed_demo_home_goods_drafts requires an active state and county.")
        home_garden_category = Category.objects.filter(
            vertical__slug="home-garden", slug="furniture", is_active=True
        ).first()
        appliances_category = Category.objects.filter(
            vertical__slug="appliances", slug="kitchen-appliances", is_active=True
        ).first()
        if home_garden_category is None or appliances_category is None:
            raise CommandError(
                "seed_demo_home_goods_drafts requires Home & Garden and Appliances "
                "catalog categories."
            )

        common_values = {
            "state": state,
            "county": county,
            "city": county.name,
            "currency": "USD",
        }
        home_garden_title = "Demo private patio table draft"
        if not Listing.objects.filter(seller=profiles[0], title=home_garden_title).exists():
            create_home_garden_draft(
                seller=profiles[0],
                listing_values={
                    **common_values,
                    "category": home_garden_category,
                    "title": home_garden_title,
                    "description": "Local-only private Home & Garden draft.",
                    "price_minor": 12500,
                },
                home_goods_values={
                    "item_type": "Patio table",
                    "brand": "Demo",
                    "condition": "good",
                    "working_status": "working",
                    "dimensions": "48 in diameter",
                    "fulfillment_preference": "pickup",
                },
            )

        appliances_title = "Demo private refrigerator draft"
        if not Listing.objects.filter(seller=profiles[1], title=appliances_title).exists():
            create_appliances_draft(
                seller=profiles[1],
                listing_values={
                    **common_values,
                    "category": appliances_category,
                    "title": appliances_title,
                    "description": "Local-only private Appliances draft.",
                    "price_minor": 30000,
                },
                home_goods_values={
                    "item_type": "Refrigerator",
                    "brand": "Demo",
                    "condition": "good",
                    "working_status": "working",
                    "dimensions": "30 in W x 32 in D x 66 in H",
                    "fulfillment_preference": "either",
                },
            )
        self.stdout.write(self.style.SUCCESS("Seeded bounded private Home Goods demo drafts."))
