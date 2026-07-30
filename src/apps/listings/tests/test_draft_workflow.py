from __future__ import annotations

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse

from apps.accounts.models import SellerProfile, User
from apps.catalog.models import (
    Category,
    ListingKind,
    ListingKindPriceMode,
    ListingProduct,
    Vertical,
)
from apps.listings.models import Listing, ListingStatus
from apps.listings.services import create_auto_draft, update_auto_draft
from apps.locations.models import County, State

pytestmark = pytest.mark.django_db


@pytest.fixture
def autos_reference() -> tuple[Vertical, Category, State, County]:
    autos = Vertical.objects.create(name="Autos", slug="autos")
    cars = Category.objects.create(vertical=autos, name="Cars", slug="cars")
    texas = State.objects.create(
        fips="48", usps_code="TX", name="Texas", slug="texas", is_active=True
    )
    potter = County.objects.create(
        fips="48375", state=texas, name="Potter", slug="potter", is_active=True
    )
    return autos, cars, texas, potter


@pytest.fixture
def seller() -> SellerProfile:
    user = User.objects.create_user(email="seller@example.com", password="test-password")
    return SellerProfile.objects.create(user=user, display_name="Seller")


def auto_values() -> dict[str, object]:
    return {
        "vehicle_type": "car",
        "year": 2020,
        "make": "Ford",
        "model": "Mustang",
        "trim": "GT",
        "mileage": 12000,
        "title_status": "clean",
        "vin": "1HGCM82633A004352",
    }


def listing_values(category: Category, state: State, county: County) -> dict[str, object]:
    return {
        "category": category,
        "state": state,
        "county": county,
        "city": "Amarillo",
        "title": "2020 Ford Mustang",
        "description": "Private draft",
        "price_minor": 3250000,
        "currency": "USD",
    }


def test_create_auto_draft_creates_compatible_private_records(
    seller: SellerProfile, autos_reference: tuple[Vertical, Category, State, County]
) -> None:
    autos, category, state, county = autos_reference

    listing = create_auto_draft(
        seller=seller,
        listing_values=listing_values(category, state, county),
        auto_values=auto_values(),
    )

    assert listing.status == ListingStatus.DRAFT
    assert listing.vertical == autos
    assert listing.auto_details.vin == "1HGCM82633A004352"


def test_listing_rejects_cross_model_location(
    seller: SellerProfile, autos_reference: tuple[Vertical, Category, State, County]
) -> None:
    autos, category, _state, county = autos_reference
    other_state = State.objects.create(fips="40", usps_code="OK", name="Oklahoma", slug="oklahoma")
    invalid_listing = Listing(
        seller=seller,
        vertical=autos,
        category=category,
        state=other_state,
        county=county,
        city="Amarillo",
        title="Invalid",
        description="Invalid",
        price_minor=100,
        currency="USD",
    )

    with pytest.raises(ValidationError, match="county must belong"):
        invalid_listing.full_clean()


def test_database_rejects_non_draft_status(
    seller: SellerProfile, autos_reference: tuple[Vertical, Category, State, County]
) -> None:
    autos, category, state, county = autos_reference
    with pytest.raises(IntegrityError), transaction.atomic():
        Listing.objects.create(
            seller=seller,
            vertical=autos,
            category=category,
            state=state,
            county=county,
            city="Amarillo",
            title="Invalid state",
            description="Invalid",
            price_minor=100,
            currency="USD",
            status="active",
        )


def test_non_owner_draft_detail_returns_404(
    client: Client,
    seller: SellerProfile,
    autos_reference: tuple[Vertical, Category, State, County],
) -> None:
    _autos, category, state, county = autos_reference
    listing = create_auto_draft(
        seller=seller,
        listing_values=listing_values(category, state, county),
        auto_values=auto_values(),
    )
    other = User.objects.create_user(email="other@example.com", password="test-password")
    SellerProfile.objects.create(user=other, display_name="Other seller")
    client.force_login(other)

    response = client.get(reverse("listings:draft_detail", kwargs={"listing_id": listing.id}))

    assert response.status_code == 404


def test_owner_draft_detail_omits_vin(
    client: Client,
    seller: SellerProfile,
    autos_reference: tuple[Vertical, Category, State, County],
) -> None:
    _autos, category, state, county = autos_reference
    listing = create_auto_draft(
        seller=seller,
        listing_values=listing_values(category, state, county),
        auto_values=auto_values(),
    )
    client.force_login(seller.user)

    response = client.get(reverse("listings:draft_detail", kwargs={"listing_id": listing.id}))

    assert response.status_code == 200
    assert "1HGCM82633A004352" not in response.content.decode()


def test_create_page_reports_invalid_location_pair(
    client: Client,
    seller: SellerProfile,
    autos_reference: tuple[Vertical, Category, State, County],
) -> None:
    _autos, category, _state, county = autos_reference
    other_state = State.objects.create(fips="40", usps_code="OK", name="Oklahoma", slug="oklahoma")
    client.force_login(seller.user)

    response = client.post(
        reverse("listings:create_auto_draft"),
        {
            **listing_values(category, other_state, county),
            **auto_values(),
            "category": category.id,
            "state": other_state.id,
            "county": county.id,
        },
    )

    assert response.status_code == 200
    assert "county must belong" in response.content.decode()


def test_dashboard_redirects_to_seller_profile_without_profile(client: Client) -> None:
    user = User.objects.create_user(email="new@example.com", password="test-password")
    client.force_login(user)

    response = client.get(reverse("listings:dashboard"))

    assert response.status_code == 302
    assert response["Location"] == reverse("accounts:seller_profile")


def test_empty_dashboard_offers_scannable_listing_creation(
    client: Client,
    seller: SellerProfile,
) -> None:
    client.force_login(seller.user)

    response = client.get(reverse("listings:dashboard"))

    assert response.status_code == 200
    assert b"Choose a listing type" in response.content
    assert b"Automobile" in response.content
    assert b"You have no listings yet." in response.content
    assert b"Create an automobile draft" in response.content


def test_seller_profile_can_be_created(client: Client) -> None:
    user = User.objects.create_user(email="new@example.com", password="test-password")
    client.force_login(user)

    response = client.post(
        reverse("accounts:seller_profile"),
        {"display_name": "New seller", "phone": ""},
    )

    assert response.status_code == 302
    assert SellerProfile.objects.get(user=user).display_name == "New seller"


def test_create_and_edit_draft_pages(
    client: Client,
    seller: SellerProfile,
    autos_reference: tuple[Vertical, Category, State, County],
) -> None:
    _autos, category, state, county = autos_reference
    client.force_login(seller.user)
    payload = {
        **listing_values(category, state, county),
        **auto_values(),
        "category": category.id,
        "state": state.id,
        "county": county.id,
    }

    create_response = client.post(reverse("listings:create_auto_draft"), payload)
    listing = Listing.objects.get(seller=seller)
    edit_response = client.post(
        reverse("listings:edit_auto_draft", kwargs={"listing_id": listing.id}),
        {**payload, "title": "Edited Mustang"},
    )

    assert create_response.status_code == 302
    assert edit_response.status_code == 302
    listing.refresh_from_db()
    assert listing.title == "Edited Mustang"


def test_update_auto_draft_rejects_non_owner(
    seller: SellerProfile, autos_reference: tuple[Vertical, Category, State, County]
) -> None:
    _autos, category, state, county = autos_reference
    listing = create_auto_draft(
        seller=seller,
        listing_values=listing_values(category, state, county),
        auto_values=auto_values(),
    )
    other = SellerProfile.objects.create(
        user=User.objects.create_user(email="other@example.com", password="test-password"),
        display_name="Other",
    )

    with pytest.raises(PermissionDenied, match="Only the listing owner"):
        update_auto_draft(
            listing_id=listing.id,
            seller=other,
            listing_values=listing_values(category, state, county),
            auto_values=auto_values(),
        )


@override_settings(DEBUG=True)
def test_development_seed_is_idempotent() -> None:
    call_command("seed_texas_autos")
    call_command("seed_texas_autos")

    assert State.objects.filter(fips="48").count() == 1
    assert County.objects.filter(fips__in=("48375", "48381")).count() == 2
    assert Category.objects.filter(vertical__slug="autos").count() == 6
    autos_kind = ListingKind.objects.get(vertical__slug="autos", name="Automobile")
    assert set(
        ListingKindPriceMode.objects.filter(listing_kind=autos_kind).values_list(
            "price_mode", flat=True
        )
    ) == {"fixed", "negotiable", "contact"}
    assert set(
        ListingProduct.objects.filter(listing_kind=autos_kind).values_list(
            "product_code", flat=True
        )
    ) == {"AUTOS_NEW_FIXED", "AUTOS_NEW_CONTACT"}


@override_settings(DEBUG=False)
def test_development_seed_refuses_non_debug() -> None:
    with pytest.raises(CommandError, match="DEBUG"):
        call_command("seed_texas_autos")
