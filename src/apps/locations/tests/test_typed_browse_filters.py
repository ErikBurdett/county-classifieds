from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import SellerProfile, User
from apps.catalog.models import Category, Vertical
from apps.listings.models import (
    AgEquipmentDetails,
    HomeDetails,
    HomeGoodsDetails,
    Listing,
    ListingStatus,
    LivestockDetails,
    PastureDetails,
    RentalDetails,
)
from apps.listings.selectors import public_listings
from apps.locations.forms import PublicBrowseForm, apply_public_filters
from apps.locations.models import County, State

pytestmark = pytest.mark.django_db


@pytest.fixture
def typed_inventory() -> dict[str, Listing]:
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
    seller = SellerProfile.objects.create(
        user=User.objects.create_user(email="typed-filters@example.test", password="not-used"),
        display_name="Typed filters seller",
    )

    def listing(slug: str, title: str) -> Listing:
        vertical, _created = Vertical.objects.get_or_create(name=slug.title(), slug=slug)
        category, _created = Category.objects.get_or_create(
            vertical=vertical, name=f"{slug} listings", slug=f"{slug}-listings"
        )
        return Listing.objects.create(
            seller=seller,
            vertical=vertical,
            category=category,
            state=state,
            county=county,
            city="Amarillo",
            title=title,
            description="Public typed inventory",
            status=ListingStatus.PUBLISHED,
            published_at=timezone.now(),
        )

    home = listing("real-estate", "Three bedroom home")
    HomeDetails.objects.create(
        listing=home,
        property_type="house",
        beds=3,
        baths=Decimal("2.5"),
        square_feet=1800,
        general_area="North Amarillo",
    )
    rental = listing("rentals", "Pet-friendly rental")
    RentalDetails.objects.create(
        listing=rental,
        rental_type="apartment",
        monthly_rent_minor=120_000,
        beds=2,
        baths=Decimal("1.0"),
        available_date=date.today(),
        pets_policy="allowed",
        lease_term_months=12,
        general_area="Central Amarillo",
    )
    equipment = listing("farm-ranch", "John Deere tractor")
    AgEquipmentDetails.objects.create(
        listing=equipment,
        equipment_type="tractor",
        make="John Deere",
        model="5075E",
        year=2020,
        hours=900,
        condition="used",
    )
    pasture = listing("farm-ranch", "Fenced pasture")
    PastureDetails.objects.create(
        listing=pasture,
        acreage=Decimal("50.00"),
        water_available=True,
        fenced=True,
        lease_term="Annual",
        available_date=date.today(),
    )
    livestock = listing("livestock-animals", "Angus cattle")
    LivestockDetails.objects.create(
        listing=livestock,
        species="cattle",
        breed="Angus",
        animal_class="Heifer",
        head_count=20,
        sale_unit="head",
    )
    goods = listing("home-garden", "Working Whirlpool washer")
    HomeGoodsDetails.objects.create(
        listing=goods,
        item_type="Washer",
        brand="Whirlpool",
        condition="good",
        working_status="working",
        fulfillment_preference="pickup",
    )
    return {
        "home": home,
        "rental": rental,
        "equipment": equipment,
        "pasture": pasture,
        "livestock": livestock,
        "goods": goods,
    }


@pytest.mark.parametrize(
    ("inventory_key", "parameters"),
    [
        (
            "home",
            {
                "home_property_type": "house",
                "home_min_beds": "3",
                "home_min_baths": "2.0",
                "home_min_square_feet": "1500",
            },
        ),
        (
            "rental",
            {"rental_type": "apartment", "rental_min_beds": "2", "rental_pets_policy": "allowed"},
        ),
        (
            "equipment",
            {
                "equipment_type": "tractor",
                "equipment_make": "John Deere",
                "equipment_min_year": "2019",
                "equipment_max_hours": "1000",
                "equipment_condition": "used",
            },
        ),
        (
            "pasture",
            {
                "pasture_min_acreage": "40",
                "pasture_water_available": "yes",
                "pasture_fenced": "yes",
                "pasture_lease_term": "Annual",
            },
        ),
        (
            "livestock",
            {
                "livestock_species": "cattle",
                "livestock_breed": "Angus",
                "livestock_sale_unit": "head",
                "livestock_min_head_count": "10",
            },
        ),
        (
            "goods",
            {
                "goods_item_type": "Washer",
                "goods_brand": "Whirlpool",
                "goods_condition": "good",
                "goods_working_status": "working",
            },
        ),
    ],
)
def test_typed_filters_use_fixed_public_lookups(
    typed_inventory: dict[str, Listing], inventory_key: str, parameters: dict[str, str]
) -> None:
    expected = typed_inventory[inventory_key]
    form = PublicBrowseForm(
        {"vertical": str(expected.vertical_id), "q": expected.title, **parameters},
        state=expected.state,
    )

    assert form.is_valid(), form.errors
    assert list(apply_public_filters(public_listings(), form)) == [expected]


def test_cross_vertical_typed_filters_are_dropped_from_urls_and_chips(
    client: Client, typed_inventory: dict[str, Listing]
) -> None:
    home = typed_inventory["home"]

    response = client.get(
        "/texas/potter/",
        {
            "vertical": str(home.vertical_id),
            "q": "Three bedroom",
            "home_min_beds": "3",
            "make": "Ford",
            "untrusted": "never-copy-this",
        },
    )

    assert response.status_code == 200
    assert b"Three bedroom home" in response.content
    assert b'name="make"' not in response.content
    assert b"Ford" not in response.content
    assert b"untrusted" not in response.content
    assert response.context["pagination_query"] == (
        f"q=Three+bedroom&vertical={home.vertical_id}&home_min_beds=3"
    )
    assert b"Minimum beds: 3" in response.content


def test_typed_filter_form_has_no_fields_until_a_supported_vertical_is_selected(
    typed_inventory: dict[str, Listing],
) -> None:
    state = typed_inventory["home"].state
    form = PublicBrowseForm({"home_min_beds": "3", "make": "Ford"}, state=state)

    assert form.is_valid()
    assert "home_min_beds" not in form.fields
    assert "make" not in form.fields
    assert form.query_parameters() == []
