from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, cast
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.accounts.models import SellerProfile, User
from apps.catalog.models import CatalogPostingProfile, Category, Vertical
from apps.listings.models import (
    AgEquipmentDetails,
    GenericListingDetails,
    HomeDetails,
    HomeGoodsDetails,
    Listing,
    ListingCategoryTag,
    ListingCustomField,
    ListingSellerTag,
    LivestockDetails,
    PastureDetails,
    RentalDetails,
)
from apps.listings.search import (
    public_search_terms,
    public_search_vector,
    rebuild_public_search_document,
)
from apps.listings.selectors import public_listings
from apps.listings.services import create_auto_draft, publish_auto_listing
from apps.locations.forms import PublicBrowseForm, apply_public_filters
from apps.locations.models import County, State

pytestmark = pytest.mark.django_db


@pytest.fixture
def public_auto() -> Listing:
    seller = SellerProfile.objects.create(
        user=User.objects.create_user(email="search@example.test", password="not-used"),
        display_name="Search seller",
    )
    vertical = Vertical.objects.create(name="Autos", slug="autos")
    category = Category.objects.create(vertical=vertical, name="Cars", slug="cars")
    state = State.objects.create(
        fips="48",
        usps_code="TX",
        name="Texas",
        slug="texas",
        is_active=True,
        is_network_enabled=True,
    )
    county = County.objects.create(
        fips="48375",
        state=state,
        name="Potter",
        slug="potter",
        is_active=True,
        is_network_enabled=True,
    )
    listing = create_auto_draft(
        seller=seller,
        listing_values={
            "category": category,
            "state": state,
            "county": county,
            "city": "Amarillo",
            "title": "Public Mustang",
            "description": "A public listing description.",
        },
        auto_values={
            "vehicle_type": "car",
            "year": 2020,
            "make": "Ford",
            "model": "Mustang",
            "trim": "",
            "mileage": 1,
            "title_status": "clean",
            "vin": "1HGCM82633A004352",
        },
    )
    return publish_auto_listing(listing_id=listing.id)


def test_sqlite_fallback_searches_safe_public_fields_not_vin(public_auto: Listing) -> None:
    listing = public_auto
    form = PublicBrowseForm({"q": "Mustang"}, state=listing.state)

    assert form.is_valid()
    assert list(apply_public_filters(public_listings(), form)) == [listing]

    private_form = PublicBrowseForm({"q": "1HGCM82633A004352"}, state=listing.state)
    assert private_form.is_valid()
    assert not apply_public_filters(public_listings(), private_form).exists()


def test_public_document_terms_exclude_private_auto_fields(public_auto: Listing) -> None:
    terms = public_search_terms(public_auto)
    flattened = " ".join(term for group in terms.values() for term in group)

    assert "Public Mustang" in terms["A"]
    assert "Ford" in terms["B"]
    assert "Amarillo" in terms["C"]
    assert "public listing description" in flattened
    assert "1HGCM82633A004352" not in flattened


def test_published_taxonomy_tags_are_searchable_but_custom_fields_are_not(
    public_auto: Listing,
) -> None:
    secondary = Category.objects.create(
        vertical=public_auto.vertical, name="Convertible", slug="convertible"
    )
    ListingCategoryTag.objects.create(listing=public_auto, category=public_auto.category)
    ListingCategoryTag.objects.create(listing=public_auto, category=secondary)
    seller_tag = ListingSellerTag(listing=public_auto, value="Summer cruiser")
    seller_tag.full_clean()
    seller_tag.save()
    custom_field = ListingCustomField(
        listing=public_auto, label="Included accessory", value="Garage cover"
    )
    custom_field.full_clean()
    custom_field.save()

    terms = public_search_terms(public_auto)
    flattened = " ".join(term for group in terms.values() for term in group)

    assert "Convertible" in terms["B"]
    assert "Summer cruiser" in terms["B"]
    assert "Garage cover" not in flattened
    tag_form = PublicBrowseForm({"q": "Summer cruiser"}, state=public_auto.state)
    field_form = PublicBrowseForm({"q": "Garage cover"}, state=public_auto.state)
    assert tag_form.is_valid() and field_form.is_valid()
    assert list(apply_public_filters(public_listings(), tag_form)) == [public_auto]
    assert not apply_public_filters(public_listings(), field_form).exists()
    public_auto.status = "in_review"
    public_auto.published_at = None
    public_auto.save(update_fields=("status", "published_at", "updated_at"))
    assert not apply_public_filters(public_listings(), tag_form).exists()


def test_public_document_uses_only_approved_typed_descriptors(public_auto: Listing) -> None:
    """Each supported typed detail contributes its defined public search labels."""

    def listing_for(vertical_slug: str, title: str) -> Listing:
        vertical = Vertical.objects.create(name=vertical_slug, slug=vertical_slug)
        category = Category.objects.create(
            vertical=vertical, name=f"{vertical_slug} category", slug=f"{vertical_slug}-category"
        )
        return Listing.objects.create(
            seller=public_auto.seller,
            vertical=vertical,
            category=category,
            state=public_auto.state,
            county=public_auto.county,
            city="Amarillo",
            title=title,
            description="Public description",
        )

    equipment = listing_for("equipment-search", "Tractor")
    AgEquipmentDetails.objects.create(
        listing=equipment,
        equipment_type="tractor",
        make="John Deere",
        model="5075E",
        condition="used",
    )
    goods = listing_for("goods-search", "Washer")
    HomeGoodsDetails.objects.create(
        listing=goods,
        item_type="Washer",
        brand="Whirlpool",
        condition="good",
        working_status="working",
        fulfillment_preference="pickup",
    )
    livestock = listing_for("livestock-search", "Cattle")
    LivestockDetails.objects.create(
        listing=livestock,
        species="cattle",
        breed="Angus",
        animal_class="Heifer",
        head_count=1,
        sale_unit="head",
    )
    home = listing_for("home-search", "Home")
    HomeDetails.objects.create(listing=home, property_type="land")
    rental = listing_for("rental-search", "Rental")
    RentalDetails.objects.create(
        listing=rental,
        rental_type="storage",
        monthly_rent_minor=100,
        available_date=date.today(),
        pets_policy="not_allowed",
    )
    pasture = listing_for("pasture-search", "Pasture")
    PastureDetails.objects.create(
        listing=pasture,
        acreage=Decimal("10.5"),
        water_available=True,
        fenced=True,
        lease_term="Annual",
        available_date=date.today(),
    )

    assert {"John Deere", "5075E", "Tractor"} <= set(public_search_terms(equipment)["B"])
    assert {"Whirlpool", "Washer"} <= set(public_search_terms(goods)["B"])
    assert {"Cattle", "Angus", "Heifer"} <= set(public_search_terms(livestock)["B"])
    assert "Land" in public_search_terms(home)["B"]
    assert "Storage" in public_search_terms(rental)["B"]
    assert {"10.5 acres", "water available", "fenced", "Annual"} <= set(
        public_search_terms(pasture)["B"]
    )


def test_sqlite_blank_search_is_a_safe_noop(public_auto: Listing) -> None:
    form = PublicBrowseForm({"q": "   "}, state=public_auto.state)

    assert form.is_valid()
    assert list(apply_public_filters(public_listings(), form)) == [public_auto]


def test_sqlite_document_rebuild_is_a_noop_but_vector_is_constructible(
    public_auto: Listing,
) -> None:
    vector = public_search_vector(public_auto)
    rebuild_public_search_document(listing=public_auto)
    public_auto.refresh_from_db()

    assert vector is not None
    assert public_auto.search_document is None


def test_rebuild_command_rejects_sqlite_without_writes(public_auto: Listing) -> None:
    with pytest.raises(CommandError, match="PostgreSQL is required"):
        call_command("rebuild_listing_search_documents")

    public_auto.refresh_from_db()
    assert public_auto.search_document is None


def test_rebuild_command_batches_in_stable_uuid_order(public_auto: Listing) -> None:
    later = Listing.objects.create(
        seller=public_auto.seller,
        vertical=public_auto.vertical,
        category=public_auto.category,
        state=public_auto.state,
        county=public_auto.county,
        city="Amarillo",
        title="Later listing",
        description="Public description",
    )
    rebuilt_ids: list[object] = []

    with (
        patch(
            "apps.listings.management.commands.rebuild_listing_search_documents.postgres_search_available",
            return_value=True,
        ),
        patch(
            "apps.listings.management.commands.rebuild_listing_search_documents."
            "rebuild_public_search_document",
            side_effect=lambda *, listing: rebuilt_ids.append(listing.id),
        ),
    ):
        call_command("rebuild_listing_search_documents", batch_size=1, max_batches=2)

    assert rebuilt_ids == sorted((public_auto.id, later.id), key=str)


def test_rebuild_command_prefetches_taxonomy_and_generic_profile_relations(
    public_auto: Listing,
) -> None:
    vertical = Vertical.objects.create(name="Services", slug="services")
    category = Category.objects.create(vertical=vertical, name="Cleaning", slug="cleaning")
    secondary = Category.objects.create(vertical=vertical, name="Landscaping", slug="landscaping")
    CatalogPostingProfile.objects.create(category=category)
    listings: list[Listing] = []
    for index in range(4):
        listing = Listing.objects.create(
            seller=public_auto.seller,
            vertical=vertical,
            category=category,
            state=public_auto.state,
            county=public_auto.county,
            city="Amarillo",
            title=f"Generic rebuild {index}",
            description="Public description",
        )
        GenericListingDetails.objects.create(
            listing=listing, price_mode="contact", postal_code="00000", attributes={}
        )
        ListingCategoryTag.objects.create(listing=listing, category=category)
        ListingCategoryTag.objects.create(listing=listing, category=secondary)
        seller_tag = ListingSellerTag(listing=listing, value=f"rebuild tag {index}")
        seller_tag.full_clean()
        seller_tag.save()
        listings.append(listing)

    observed: list[object] = []

    def record_public_terms(*, listing: Listing) -> None:
        observed.append(listing.id)
        public_search_terms(listing)

    with (
        patch(
            "apps.listings.management.commands.rebuild_listing_search_documents."
            "postgres_search_available",
            return_value=True,
        ),
        patch(
            "apps.listings.management.commands.rebuild_listing_search_documents."
            "rebuild_public_search_document",
            side_effect=record_public_terms,
        ),
        CaptureQueriesContext(connection) as queries,
    ):
        call_command("rebuild_listing_search_documents", batch_size=5, max_batches=1)

    sql = "\n".join(query["sql"] for query in queries.captured_queries).lower()
    assert set(observed) == {public_auto.id, *(listing.id for listing in listings)}
    assert len(queries) <= 8
    assert sql.count('from "listings_listingcategorytag"') == 1
    assert sql.count('from "listings_listingsellertag"') == 1
    assert 'from "catalog_catalogpostingfield"' in sql


@pytest.mark.skipif(connection.vendor != "postgresql", reason="requires PostgreSQL FTS")
def test_postgres_document_search_uses_weighted_rank(public_auto: Listing) -> None:
    description_match = create_auto_draft(
        seller=public_auto.seller,
        listing_values={
            "category": public_auto.category,
            "state": public_auto.state,
            "county": public_auto.county,
            "city": "Amarillo",
            "title": "Other vehicle",
            "description": "Mustang",
        },
        auto_values={
            "vehicle_type": "car",
            "year": 2020,
            "make": "Ford",
            "model": "Other",
            "trim": "",
            "mileage": 2,
            "title_status": "clean",
            "vin": "1HGCM82633A004353",
        },
    )
    description_match = publish_auto_listing(listing_id=description_match.id)
    rebuild_public_search_document(listing=public_auto)
    rebuild_public_search_document(listing=description_match)
    form = PublicBrowseForm({"q": "Public Mustang"}, state=public_auto.state)

    assert form.is_valid()
    results = apply_public_filters(public_listings(), form)
    assert list(results) == [public_auto]
    assert "search_rank" in results.query.annotations

    rank_form = PublicBrowseForm({"q": "Mustang"}, state=public_auto.state)
    assert rank_form.is_valid()
    ranked_results = list(apply_public_filters(public_listings(), rank_form))
    ranks: dict[object, Any] = {
        result.id: cast(Any, result).search_rank for result in ranked_results
    }
    assert ranks[public_auto.id] > ranks[description_match.id]
    assert [result.id for result in ranked_results] == [public_auto.id, description_match.id]

    private_form = PublicBrowseForm({"q": "1HGCM82633A004352"}, state=public_auto.state)
    assert private_form.is_valid()
    assert not apply_public_filters(public_listings(), private_form).exists()
