from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError, connection, transaction
from django.test import Client
from django.urls import reverse

from apps.accounts.models import SellerProfile, User
from apps.catalog.models import Category, Vertical
from apps.listings.models import HomeDetails, Listing, ListingStatus, RentalDetails
from apps.listings.services import (
    create_home_draft,
    create_rental_draft,
    update_home_draft,
    update_rental_draft,
)
from apps.locations.models import County, State

pytestmark = pytest.mark.django_db

DetailValues = Callable[[], dict[str, object]]
DraftUpdateService = Callable[..., Listing]


@pytest.fixture
def property_references() -> tuple[Category, Category, State, County]:
    homes = Vertical.objects.create(name="Real Estate", slug="real-estate")
    rentals = Vertical.objects.create(name="Rentals", slug="rentals")
    home_category = Category.objects.create(vertical=homes, name="Homes", slug="homes-for-sale")
    rental_category = Category.objects.create(
        vertical=rentals, name="Homes for Rent", slug="homes-for-rent"
    )
    state = State.objects.create(
        fips="48", usps_code="TX", name="Texas", slug="texas", is_active=True
    )
    county = County.objects.create(
        fips="48375", state=state, name="Potter", slug="potter", is_active=True
    )
    return home_category, rental_category, state, county


@pytest.fixture
def seller() -> SellerProfile:
    user = User.objects.create_user(email="property@example.com", password="test-password")
    return SellerProfile.objects.create(user=user, display_name="Property seller")


def listing_values(
    category: Category, state: State, county: County, title: str
) -> dict[str, object]:
    return {
        "category": category,
        "state": state,
        "county": county,
        "city": "Amarillo",
        "title": title,
        "description": "Private property draft",
        "price_minor": 100000,
        "currency": "USD",
    }


def home_values() -> dict[str, object]:
    return {
        "property_type": "house",
        "beds": 3,
        "baths": Decimal("2.0"),
        "square_feet": 1800,
        "year_built": 2005,
        "lot_size": Decimal("0.20"),
        "lot_size_unit": "acres",
        "street_address": "123 Private Lane",
        "address_line_2": "",
        "postal_code": "79101",
        "general_area": "Near downtown",
        "exact_address_public": False,
    }


def rental_values() -> dict[str, object]:
    return {
        "rental_type": "apartment",
        "monthly_rent_minor": 125000,
        "security_deposit_minor": 125000,
        "beds": 2,
        "baths": Decimal("1.0"),
        "available_date": date(2026, 8, 1),
        "pets_policy": "case_by_case",
        "lease_term_months": 12,
        "flexible_term": False,
        "street_address": "456 Private Lane",
        "address_line_2": "",
        "postal_code": "79101",
        "general_area": "Near the park",
        "exact_address_public": False,
    }


def test_create_property_drafts_use_fixed_verticals_and_private_addresses(
    seller: SellerProfile, property_references: tuple[Category, Category, State, County]
) -> None:
    home_category, rental_category, state, county = property_references
    home = create_home_draft(
        seller=seller,
        listing_values=listing_values(home_category, state, county, "Home draft"),
        home_values=home_values(),
    )
    rental = create_rental_draft(
        seller=seller,
        listing_values=listing_values(rental_category, state, county, "Rental draft"),
        rental_values=rental_values(),
    )

    assert home.status == ListingStatus.DRAFT
    assert home.vertical.slug == "real-estate"
    assert home.home_details.exact_address_public is False
    assert rental.vertical.slug == "rentals"
    assert rental.rental_details.exact_address_public is False


@pytest.mark.parametrize(
    ("details", "expected_field"),
    [
        ({"property_type": "house", "beds": None}, "beds"),
        ({"property_type": "land", "lot_size": Decimal("-1.00")}, "lot_size"),
        (
            {"property_type": "house", "exact_address_public": True, "street_address": ""},
            "street_address",
        ),
    ],
)
def test_home_details_validate_conditional_and_private_fields(
    details: dict[str, object], expected_field: str
) -> None:
    home = HomeDetails(**{**home_values(), **details})
    with pytest.raises(ValidationError) as error:
        home.full_clean()
    assert expected_field in error.value.message_dict


@pytest.mark.parametrize(
    ("details", "expected_field"),
    [
        ({"rental_type": "apartment", "beds": None}, "beds"),
        ({"monthly_rent_minor": -1}, "monthly_rent_minor"),
        ({"flexible_term": True, "lease_term_months": 12}, "lease_term_months"),
        ({"exact_address_public": True, "street_address": ""}, "street_address"),
    ],
)
def test_rental_details_validate_conditional_and_private_fields(
    details: dict[str, object], expected_field: str
) -> None:
    rental = RentalDetails(**{**rental_values(), **details})
    with pytest.raises(ValidationError) as error:
        rental.full_clean()
    assert expected_field in error.value.message_dict


@pytest.mark.parametrize(
    ("service", "detail_values", "vertical"),
    [
        (update_home_draft, home_values, "real-estate"),
        (update_rental_draft, rental_values, "rentals"),
    ],
)
def test_property_update_services_lock_owner_and_drafts(
    seller: SellerProfile,
    property_references: tuple[Category, Category, State, County],
    service: DraftUpdateService,
    detail_values: DetailValues,
    vertical: str,
) -> None:
    home_category, rental_category, state, county = property_references
    if vertical == "real-estate":
        listing = create_home_draft(
            seller=seller,
            listing_values=listing_values(home_category, state, county, "Home draft"),
            home_values=home_values(),
        )
        values_key = "home_values"
    else:
        listing = create_rental_draft(
            seller=seller,
            listing_values=listing_values(rental_category, state, county, "Rental draft"),
            rental_values=rental_values(),
        )
        values_key = "rental_values"
    other = SellerProfile.objects.create(
        user=User.objects.create_user(
            email=f"other-{vertical}@example.com", password="test-password"
        ),
        display_name=f"Other {vertical}",
    )

    with pytest.raises(PermissionDenied):
        service(
            listing_id=listing.id,
            seller=other,
            listing_values=listing_values(listing.category, state, county, "Changed"),
            **{values_key: detail_values()},
        )


@pytest.mark.parametrize(
    "case",
    [
        ("create_home_draft", "create_home_draft", "home_draft_detail", home_values),
        ("create_rental_draft", "create_rental_draft", "rental_draft_detail", rental_values),
    ],
)
def test_property_requests_are_private_and_owner_scoped(
    client: Client,
    seller: SellerProfile,
    property_references: tuple[Category, Category, State, County],
    case: tuple[str, str, str, DetailValues],
) -> None:
    create_name, route_name, detail_name, payload_values = case
    home_category, rental_category, state, county = property_references
    category = home_category if create_name == "create_home_draft" else rental_category
    response = client.get(reverse(f"listings:{route_name}"))
    assert response.status_code == 302

    client.force_login(seller.user)
    payload = {
        **listing_values(category, state, county, f"{create_name} title"),
        **payload_values(),
        "category": category.id,
        "state": state.id,
        "county": county.id,
    }
    response = client.post(reverse(f"listings:{route_name}"), payload)
    assert response.status_code == 302
    listing = Listing.objects.get(seller=seller, title=f"{create_name} title")
    response = client.get(reverse(f"listings:{detail_name}", kwargs={"listing_id": listing.id}))
    assert response.status_code == 200
    assert b"Private Lane" in response.content

    other = User.objects.create_user(
        email=f"{create_name}-other@example.com", password="test-password"
    )
    SellerProfile.objects.create(user=other, display_name=f"{create_name} other")
    client.force_login(other)
    response = client.get(reverse(f"listings:{detail_name}", kwargs={"listing_id": listing.id}))
    assert response.status_code == 404


@pytest.mark.skipif(connection.vendor != "postgresql", reason="PostgreSQL trigger coverage")
def test_postgresql_rejects_incompatible_property_detail_and_vertical_change(
    seller: SellerProfile, property_references: tuple[Category, Category, State, County]
) -> None:
    home_category, rental_category, state, county = property_references
    home = create_home_draft(
        seller=seller,
        listing_values=listing_values(home_category, state, county, "Home draft"),
        home_values=home_values(),
    )
    with pytest.raises(DatabaseError), transaction.atomic():
        home.vertical = rental_category.vertical
        home.category = rental_category
        home.save(update_fields=("vertical", "category"))

    rental_listing = Listing.objects.create(
        seller=seller,
        vertical=home_category.vertical,
        category=home_category,
        state=state,
        county=county,
        city="Amarillo",
        title="Wrong details",
        description="Wrong details",
        price_minor=100,
        currency="USD",
    )
    with pytest.raises(DatabaseError), transaction.atomic():
        RentalDetails.objects.create(listing=rental_listing, **rental_values())
