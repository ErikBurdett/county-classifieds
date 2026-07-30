from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from apps.accounts.models import SellerProfile, User
from apps.catalog.models import Category, PostingFieldType
from apps.listings.models import Listing, ListingStatus
from apps.listings.services import create_unified_draft, publish_demo_listing
from apps.listings.workflows import resolve_listing_workflow
from apps.locations.models import County, ZipCountyReference

DEMO_SELLER_EMAIL = "generic-taxonomy-demo@local.test"
DEMO_ZIP_SOURCE_NAME = "Local generic taxonomy demo"
DEMO_ZIP_SOURCE_URL = "https://local.test/demo-generic-taxonomy"
DEMO_ZIP_RELEASE_DATE = date(2026, 7, 30)


@dataclass(frozen=True)
class GenericDemoExemplar:
    vertical_slug: str
    category_slug: str
    secondary_category_slug: str | None
    title: str
    seller_tag: str
    custom_field_label: str
    custom_field_value: str


EXEMPLARS = (
    GenericDemoExemplar(
        vertical_slug="services",
        category_slug="cleaning",
        secondary_category_slug="landscaping",
        title="Synthetic taxonomy fixture: services",
        seller_tag="directory-service-demo",
        custom_field_label="Fixture availability",
        custom_field_value="Weekday demonstration",
    ),
    GenericDemoExemplar(
        vertical_slug="business-industrial",
        category_slug="food-service-equipment",
        secondary_category_slug="janitorial-equipment",
        title="Synthetic taxonomy fixture: business",
        seller_tag="directory-business-demo",
        custom_field_label="Fixture use",
        custom_field_value="Training demonstration",
    ),
    GenericDemoExemplar(
        vertical_slug="jobs",
        category_slug="full-time-jobs",
        secondary_category_slug="construction-jobs",
        title="Synthetic taxonomy fixture: jobs",
        seller_tag="directory-jobs-demo",
        custom_field_label="Fixture schedule",
        custom_field_value="Daytime demonstration",
    ),
    GenericDemoExemplar(
        vertical_slug="collectibles-art",
        category_slug="antiques",
        secondary_category_slug="memorabilia",
        title="Synthetic taxonomy fixture: collectibles",
        seller_tag="directory-collectibles-demo",
        custom_field_label="Fixture era",
        custom_field_value="Modern reproduction",
    ),
    GenericDemoExemplar(
        vertical_slug="electronics",
        category_slug="laptops",
        secondary_category_slug="tablets",
        title="Synthetic taxonomy fixture: electronics",
        seller_tag="directory-electronics-demo",
        custom_field_label="Fixture condition",
        custom_field_value="Bench-tested demonstration",
    ),
    GenericDemoExemplar(
        vertical_slug="others",
        category_slug="general",
        secondary_category_slug=None,
        title="Synthetic taxonomy fixture: others",
        seller_tag="directory-others-demo",
        custom_field_label="Fixture condition",
        custom_field_value="Safe synthetic demonstration",
    ),
)


@dataclass
class Counts:
    created: int = 0
    updated: int = 0
    unchanged: int = 0


class Command(BaseCommand):
    help = "Seed bounded published generic taxonomy/fact demos; DEBUG only."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--limit-counties", type=int, default=1)

    def handle(self, *_args: object, **options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_demo_generic_taxonomy may only run with DEBUG enabled.")
        limit = options["limit_counties"]
        if not isinstance(limit, int) or limit < 1:
            raise CommandError("--limit-counties must be a positive integer.")

        seller = self._seller()
        exemplars = self._exemplars()
        counties = list(
            County.objects.filter(
                is_active=True,
                is_network_enabled=True,
                state__is_active=True,
                state__is_network_enabled=True,
            )
            .select_related("state")
            .order_by("state__fips", "fips")[:limit]
        )
        if not counties:
            raise CommandError(
                "An active, network-enabled county is required; "
                "run a local reference/demo seed first."
            )

        counts = Counts()
        for county in counties:
            for exemplar, category, secondary_category in exemplars:
                self._seed_listing(
                    seller=seller,
                    county=county,
                    exemplar=exemplar,
                    category=category,
                    secondary_category=secondary_category,
                    counts=counts,
                )
        self.stdout.write(
            self.style.SUCCESS(
                f"Generic taxonomy demo inventory: {counts.created} created, "
                f"{counts.updated} updated, {counts.unchanged} unchanged."
            )
        )

    @staticmethod
    def _seller() -> SellerProfile:
        user, created = User.objects.get_or_create(email=DEMO_SELLER_EMAIL)
        if created:
            user.set_unusable_password()
            user.save(update_fields=("password",))
        seller, _ = SellerProfile.objects.get_or_create(
            user=user, defaults={"display_name": "Generic Taxonomy Demo Seller"}
        )
        return seller

    @staticmethod
    def _exemplars() -> list[tuple[GenericDemoExemplar, Category, Category | None]]:
        categories: list[tuple[GenericDemoExemplar, Category, Category | None]] = []
        for exemplar in EXEMPLARS:
            category = (
                Category.objects.filter(
                    vertical__slug=exemplar.vertical_slug,
                    slug=exemplar.category_slug,
                    is_active=True,
                    vertical__is_active=True,
                )
                .select_related("vertical", "posting_profile")
                .prefetch_related("posting_profile__fields")
                .first()
            )
            secondary_category = (
                Category.objects.filter(
                    vertical__slug=exemplar.vertical_slug,
                    slug=exemplar.secondary_category_slug,
                    is_active=True,
                    vertical__is_active=True,
                )
                .select_related("vertical")
                .first()
                if exemplar.secondary_category_slug is not None
                else None
            )
            if category is None or (
                exemplar.secondary_category_slug is not None and secondary_category is None
            ):
                raise CommandError(
                    f"Active {exemplar.vertical_slug} demo categories are required; "
                    "run seed_marketplace_catalog first."
                )
            if resolve_listing_workflow(category=category).typed:
                raise CommandError(
                    f"{exemplar.vertical_slug}/{exemplar.category_slug} is not a generic workflow."
                )
            categories.append((exemplar, category, secondary_category))
        return categories

    @staticmethod
    def _attributes(*, category: Category) -> dict[str, str | int | bool]:
        profile = category.posting_profile
        fields = profile.fields.all()
        attributes: dict[str, str | int | bool] = {}
        for field in fields:
            if not field.required:
                continue
            if field.field_type == PostingFieldType.TEXT:
                attributes[field.key] = "Synthetic local demonstration"
            elif field.field_type == PostingFieldType.INTEGER:
                attributes[field.key] = 1
            elif field.field_type == PostingFieldType.BOOLEAN:
                attributes[field.key] = True
            elif field.field_type == PostingFieldType.CHOICE:
                attributes[field.key] = str(field.choices[0])
        return attributes

    @staticmethod
    def _ensure_demo_zip_candidate(*, county: County) -> str:
        """Create only the DEBUG fixture's synthetic ZIP-to-county candidate."""
        postal_code = county.fips
        ZipCountyReference.objects.get_or_create(
            postal_code=postal_code,
            county=county,
            defaults={
                "source_name": DEMO_ZIP_SOURCE_NAME,
                "source_url": DEMO_ZIP_SOURCE_URL,
                "release_version": "2026-07-30",
                "release_date": DEMO_ZIP_RELEASE_DATE,
                "sha256_checksum": "0" * 64,
                "transformation_version": "local-demo-v1",
            },
        )
        return postal_code

    @staticmethod
    def _seed_listing(  # noqa: PLR0913
        *,
        seller: SellerProfile,
        county: County,
        exemplar: GenericDemoExemplar,
        category: Category,
        secondary_category: Category | None,
        counts: Counts,
    ) -> None:
        title = f"{exemplar.title} in {county.name}, {county.state.usps_code}"
        with transaction.atomic():
            listing = Listing.objects.filter(seller=seller, title=title).first()
            if listing is None:
                profile = category.posting_profile
                postal_code = Command._ensure_demo_zip_candidate(county=county)
                listing = create_unified_draft(
                    seller=seller,
                    workflow=resolve_listing_workflow(category=category),
                    listing_values={
                        "category": category,
                        "state": county.state,
                        "county": county,
                        "city": county.name,
                        "title": title,
                        "description": "Safe synthetic local taxonomy demonstration listing.",
                        "price_minor": None,
                        "currency": "",
                    },
                    detail_values={},
                    generic_values={
                        "price_mode": "contact",
                        "postal_code": postal_code,
                        "street_address": "",
                        "schema_version": profile.version,
                        "attributes": Command._attributes(category=category),
                    },
                    controlled_categories=[secondary_category]
                    if secondary_category is not None
                    else [],
                    seller_tags=[exemplar.seller_tag],
                    custom_fields=[
                        {
                            "label": exemplar.custom_field_label,
                            "value": exemplar.custom_field_value,
                        }
                    ],
                )
                publish_demo_listing(listing_id=listing.id)
                counts.created += 1
            elif listing.status != ListingStatus.PUBLISHED:
                publish_demo_listing(listing_id=listing.id)
                counts.updated += 1
            else:
                counts.unchanged += 1
