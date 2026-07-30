from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.db.models import Count

from apps.accounts.models import SellerProfile, User
from apps.catalog.models import Category
from apps.listings.models import (
    AgEquipmentDetails,
    AutoDetails,
    HomeDetails,
    HomeGoodsDetails,
    Listing,
    ListingStatus,
    LivestockDetails,
    PastureDetails,
    RentalDetails,
)
from apps.listings.services import publish_demo_listing
from apps.locations.models import County

DEMO_SELLERS = (
    "nationwide-demo-1@local.test",
    "nationwide-demo-2@local.test",
    "nationwide-demo-3@local.test",
    "nationwide-demo-4@local.test",
)
DEMO_KINDS = (
    ("autos", "Demo Auto", "auto"),
    ("real-estate", "Demo Home", "home"),
    ("rentals", "Demo Rental", "rental"),
    ("farm-ranch", "Demo Ag Equipment", "equipment"),
    ("livestock-animals", "Demo Livestock", "livestock"),
    ("farm-ranch", "Demo Pasture", "pasture"),
    ("home-garden", "Demo Home & Garden", "goods"),
    ("appliances", "Demo Appliance", "goods"),
)


@dataclass
class Counts:
    created: int = 0
    updated: int = 0
    unchanged: int = 0


class Command(BaseCommand):
    help = (
        "Seed one approved public typed demo listing per implemented type and enabled county; "
        "DEBUG only."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--limit-counties", type=int, default=None)

    def handle(self, *_args: object, **options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_nationwide_demo_inventory may only run with DEBUG enabled.")
        limit = options["limit_counties"]
        if limit is not None and (not isinstance(limit, int) or limit < 1):
            raise CommandError("--limit-counties must be a positive integer.")
        categories = self._categories()
        sellers = self._sellers()
        counties = (
            County.objects.filter(
                is_active=True,
                is_network_enabled=True,
                state__is_active=True,
                state__is_network_enabled=True,
            )
            .select_related("state")
            .order_by("state__fips", "fips")
        )
        target_counties = counties[:limit] if limit is not None else counties
        completed_counties = (
            Listing.objects.filter(
                county__in=target_counties,
                status=ListingStatus.PUBLISHED,
                title__startswith="Demo ",
            )
            .values("county_id")
            .annotate(listing_count=Count("id"))
            .filter(listing_count=len(DEMO_KINDS))
        )
        counts = Counts(unchanged=completed_counties.count() * len(DEMO_KINDS))
        counties = (
            County.objects.filter(pk__in=target_counties)
            .exclude(pk__in=completed_counties.values("county_id"))
            .select_related("state")
            .order_by("state__fips", "fips")
        )
        for county in counties.iterator(chunk_size=100):
            for kind_index, (vertical_slug, label, detail_kind) in enumerate(DEMO_KINDS):
                self._seed_listing(
                    county=county,
                    category=categories[vertical_slug],
                    seller=sellers[(int(county.fips) + kind_index) % len(sellers)],
                    label=label,
                    detail_kind=detail_kind,
                    counts=counts,
                )
        self.stdout.write(
            self.style.SUCCESS(
                f"Nationwide demo inventory: {counts.created} created, {counts.updated} updated, "
                f"{counts.unchanged} unchanged."
            )
        )

    @staticmethod
    def _categories() -> dict[str, Category]:
        categories: dict[str, Category] = {}
        for slug, _label, _detail_kind in DEMO_KINDS:
            category = (
                Category.objects.filter(vertical__slug=slug, is_active=True)
                .order_by("display_order", "id")
                .first()
            )
            if category is None:
                raise CommandError(
                    f"An active category is required for {slug}; seed the catalog first."
                )
            categories[slug] = category
        return categories

    @staticmethod
    def _sellers() -> list[SellerProfile]:
        sellers: list[SellerProfile] = []
        for index, email in enumerate(DEMO_SELLERS, start=1):
            user, created = User.objects.get_or_create(email=email)
            if created:
                user.set_unusable_password()
                user.save(update_fields=("password",))
            seller, _ = SellerProfile.objects.get_or_create(
                user=user, defaults={"display_name": f"Nationwide Demo Seller {index}"}
            )
            sellers.append(seller)
        return sellers

    @staticmethod
    def _seed_listing(  # noqa: PLR0913
        *,
        county: County,
        category: Category,
        seller: SellerProfile,
        label: str,
        detail_kind: str,
        counts: Counts,
    ) -> None:
        title = f"{label} in {county.name}, {county.state.usps_code}"
        with transaction.atomic():
            listing = Listing.objects.filter(
                title=title, county=county, vertical=category.vertical
            ).first()
            if listing is None:
                listing = Listing.objects.create(
                    seller=seller,
                    vertical=category.vertical,
                    category=category,
                    state=county.state,
                    county=county,
                    city=county.name,
                    title=title,
                    description=(
                        f"Safe nationwide demonstration {label.lower()} listing "
                        f"for {county.name} County."
                    ),
                    price_minor=100_000,
                    currency="USD",
                )
                Command._create_details(listing=listing, detail_kind=detail_kind)
                publish_demo_listing(listing_id=listing.id)
                counts.created += 1
            elif listing.status != ListingStatus.PUBLISHED:
                publish_demo_listing(listing_id=listing.id)
                counts.updated += 1
            else:
                counts.unchanged += 1

    @staticmethod
    def _create_details(*, listing: Listing, detail_kind: str) -> None:
        if detail_kind == "auto":
            AutoDetails.objects.create(
                listing=listing,
                vehicle_type="car",
                year=2022,
                make="Demo",
                model="Auto",
                mileage=10_000,
                title_status="clean",
                vin="",
            )
        elif detail_kind == "home":
            HomeDetails.objects.create(
                listing=listing,
                property_type="house",
                beds=3,
                baths="2.0",
                square_feet=1500,
                general_area="General county area",
            )
        elif detail_kind == "rental":
            RentalDetails.objects.create(
                listing=listing,
                rental_type="house",
                monthly_rent_minor=120_000,
                security_deposit_minor=0,
                beds=2,
                baths="1.0",
                available_date=date.today(),
                pets_policy="case_by_case",
                lease_term_months=12,
                general_area="General county area",
            )
        elif detail_kind == "equipment":
            AgEquipmentDetails.objects.create(
                listing=listing,
                equipment_type="tractor",
                make="Demo",
                model="Tractor",
                year=2020,
                hours=500,
                powered=True,
                condition="used",
            )
        elif detail_kind == "livestock":
            LivestockDetails.objects.create(
                listing=listing, species="cattle", head_count=10, sale_unit="head"
            )
        elif detail_kind == "pasture":
            PastureDetails.objects.create(
                listing=listing, acreage="40.00", lease_term="Annual", available_date=date.today()
            )
        else:
            HomeGoodsDetails.objects.create(
                listing=listing,
                item_type="Demo item",
                condition="good",
                working_status="working",
                fulfillment_preference="pickup",
            )
