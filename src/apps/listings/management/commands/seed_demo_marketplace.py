from __future__ import annotations

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import SellerProfile, User
from apps.catalog.models import Category
from apps.core.demo_credentials import record_local_demo_credential
from apps.listings.models import Listing
from apps.listings.services import create_auto_draft, publish_auto_listing
from apps.locations.models import County, State

DEMO_PASSWORD = "LocalDemoOnly-ChangeMe-2026!"  # noqa: S105 - DEBUG-only local fixture
DEMO_MARKETS = (
    ("Texas", "48", "TX", "texas", "Potter", "48375", "potter", "telephoneheater@local.test"),
    (
        "New Mexico",
        "35",
        "NM",
        "new-mexico",
        "Bernalillo",
        "35001",
        "bernalillo",
        "albuquerque@local.test",
    ),
    ("Colorado", "08", "CO", "colorado", "Denver", "08031", "denver", "denver@local.test"),
    ("Oklahoma", "40", "OK", "oklahoma", "Tulsa", "40143", "tulsa", "tulsa@local.test"),
)
DEMO_COUNTY_CENTROIDS = {
    "48375": (35.401010, -101.894020),
    "35001": (35.051840, -106.669080),
    "08031": (39.761850, -104.881100),
    "40143": (36.121080, -95.941960),
}


class Command(BaseCommand):
    help = "Seed deterministic local public Autos inventory; DEBUG only."

    @transaction.atomic
    def handle(self, *_args: object, **_options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_demo_marketplace may only run with DEBUG enabled.")
        call_command("seed_texas_autos", verbosity=0)
        category = Category.objects.get(vertical__slug="autos", slug="cars", is_active=True)
        for index, market in enumerate(DEMO_MARKETS):
            (
                state_name,
                state_fips,
                usps,
                state_slug,
                county_name,
                county_fips,
                county_slug,
                email,
            ) = market
            state, _ = State.objects.update_or_create(
                fips=state_fips,
                defaults={
                    "name": state_name,
                    "usps_code": usps,
                    "slug": state_slug,
                    "is_active": True,
                    "is_network_enabled": True,
                },
            )
            county, _ = County.objects.update_or_create(
                fips=county_fips,
                defaults={
                    "state": state,
                    "name": county_name,
                    "slug": county_slug,
                    "centroid_latitude": DEMO_COUNTY_CENTROIDS[county_fips][0],
                    "centroid_longitude": DEMO_COUNTY_CENTROIDS[county_fips][1],
                    "is_active": True,
                    "is_network_enabled": True,
                },
            )
            user, created = User.objects.get_or_create(email=email)
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save(update_fields=("password",))
                record_local_demo_credential(email=email, password=DEMO_PASSWORD)
            display_name = (
                "telephoneheater" if email == "telephoneheater@local.test" else email.split("@")[0]
            )
            profile, _ = SellerProfile.objects.update_or_create(
                user=user, defaults={"display_name": display_name}
            )
            for listing_number in range(3):
                title = f"{2023 - listing_number} Demo {state.usps_code} Auto {listing_number + 1}"
                listing = Listing.objects.filter(seller=profile, title=title).first()
                if listing is None:
                    listing = create_auto_draft(
                        seller=profile,
                        listing_values={
                            "category": category,
                            "state": state,
                            "county": county,
                            "city": county_name,
                            "title": title,
                            "description": f"Local demonstration vehicle in {county_name}.",
                            "price_minor": (18000 + index * 3000 + listing_number * 1000) * 100,
                            "currency": "USD",
                        },
                        auto_values={
                            "vehicle_type": "car",
                            "year": 2023 - listing_number,
                            "make": "Demo",
                            "model": f"Model {listing_number + 1}",
                            "trim": "",
                            "mileage": 12000 + listing_number * 5000,
                            "title_status": "clean",
                            "vin": "",
                        },
                    )
                if listing.status == "draft":
                    publish_auto_listing(listing_id=listing.id)
        self.stdout.write(self.style.SUCCESS("Seeded local demo marketplace inventory."))
