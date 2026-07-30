from __future__ import annotations

from typing import cast

import pytest
from django import forms
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from apps.accounts.models import SellerProfile, User
from apps.catalog.models import Category, Vertical
from apps.listings.forms import GenericListingForm
from apps.listings.models import ListingCountyPlacement
from apps.listings.services import create_generic_draft
from apps.locations.models import County, State, ZipCountyReference

pytestmark = pytest.mark.django_db


@pytest.fixture
def generic_reference() -> tuple[SellerProfile, Category, State, County, County]:
    user = User.objects.create_user(email="generic@example.com", password="password")
    seller = SellerProfile.objects.create(user=user, display_name="Generic seller")
    vertical = Vertical.objects.create(name="Services", slug="services")
    category = Category.objects.create(vertical=vertical, name="Cleaning", slug="cleaning")
    state = State.objects.create(
        fips="48", usps_code="TX", name="Texas", slug="texas", is_active=True
    )
    primary = County.objects.create(
        fips="48375", state=state, name="Potter", slug="potter", is_active=True
    )
    extra = County.objects.create(
        fips="48201", state=state, name="Harris", slug="harris", is_active=True
    )
    for county in (primary, extra):
        ZipCountyReference.objects.create(
            postal_code="77001",
            county=county,
            source_name="test",
            source_url="https://example.test/crosswalk",
            release_version="test",
            release_date="2026-07-23",
            sha256_checksum="0" * 64,
            transformation_version="test",
        )
    return seller, category, state, primary, extra


def test_generic_form_requires_loaded_zip_candidate(
    generic_reference: tuple[SellerProfile, Category, State, County, County],
) -> None:
    _seller, category, state, primary, _extra = generic_reference
    form = GenericListingForm(
        data={
            "category": category.id,
            "state": state.id,
            "county": primary.id,
            "city": "Amarillo",
            "title": "Cleaning help",
            "description": "Weekly cleaning",
            "price_mode": "contact",
            "postal_code": "99999",
            "currency": "USD",
        }
    )
    assert not form.is_valid()
    assert "postal_code" in form.errors


def test_generic_form_offers_all_active_state_counties_before_zip_verification(
    generic_reference: tuple[SellerProfile, Category, State, County, County],
) -> None:
    _seller, category, state, primary, extra = generic_reference
    unverified = County.objects.create(
        fips="48113", state=state, name="Dallas", slug="dallas", is_active=True
    )
    form = GenericListingForm(
        data={
            "vertical": category.vertical_id,
            "category": category.id,
            "state": state.id,
            "county": unverified.id,
            "city": "Dallas",
            "title": "Cleaning help",
            "description": "Weekly cleaning",
            "price_mode": "contact",
            "postal_code": "77001",
        }
    )

    county_field = cast("forms.ModelChoiceField[County]", form.fields["county"])
    county_queryset = county_field.queryset
    assert county_queryset is not None
    assert {county.id for county in county_queryset} == {
        primary.id,
        extra.id,
        unverified.id,
    }
    assert not form.is_valid()
    assert "county" in form.errors


def test_generic_form_rejects_unverified_additional_county(
    generic_reference: tuple[SellerProfile, Category, State, County, County],
) -> None:
    _seller, category, state, primary, _extra = generic_reference
    unverified = County.objects.create(
        fips="48113", state=state, name="Dallas", slug="dallas", is_active=True
    )
    form = GenericListingForm(
        data={
            "vertical": category.vertical_id,
            "category": category.id,
            "state": state.id,
            "county": primary.id,
            "additional_counties": [unverified.id],
            "city": "Amarillo",
            "title": "Cleaning help",
            "description": "Weekly cleaning",
            "price_mode": "contact",
            "postal_code": "77001",
        }
    )

    assert not form.is_valid()
    assert "additional_counties" in form.errors


def test_generic_form_converts_usd_amount_to_minor_units(
    generic_reference: tuple[SellerProfile, Category, State, County, County],
) -> None:
    _seller, category, state, primary, _extra = generic_reference
    form = GenericListingForm(
        data={
            "vertical": category.vertical_id,
            "category": category.id,
            "state": state.id,
            "county": primary.id,
            "city": "Amarillo",
            "title": "Cleaning help",
            "description": "Weekly cleaning",
            "price_mode": "fixed",
            "asking_price": "1250.50",
            "postal_code": "77001",
        }
    )

    assert form.is_valid()
    assert form.cleaned_data["price_minor"] == 125050
    assert form.cleaned_data["currency"] == "USD"


def test_generic_draft_uses_one_listing_with_unique_additional_county(
    generic_reference: tuple[SellerProfile, Category, State, County, County],
) -> None:
    seller, category, state, primary, extra = generic_reference
    listing = create_generic_draft(
        seller=seller,
        listing_values={
            "category": category,
            "state": state,
            "county": primary,
            "city": "Amarillo",
            "title": "Cleaning help",
            "description": "Weekly cleaning",
            "price_minor": None,
            "currency": "",
        },
        generic_values={
            "price_mode": "contact",
            "postal_code": "77001",
            "street_address": "1 Private Way",
        },
        additional_counties=[extra],
    )
    assert listing.generic_details.street_address == "1 Private Way"
    assert ListingCountyPlacement.objects.get(listing=listing).county == extra
    with pytest.raises(ValidationError):
        create_generic_draft(
            seller=seller,
            listing_values={
                "category": category,
                "state": state,
                "county": primary,
                "city": "Amarillo",
                "title": "Duplicate",
                "description": "Weekly cleaning",
                "price_minor": None,
                "currency": "",
            },
            generic_values={"price_mode": "contact", "postal_code": "77001", "street_address": ""},
            additional_counties=[primary],
        )


def test_generic_create_endpoints_and_owner_edit(
    client: Client,
    generic_reference: tuple[SellerProfile, Category, State, County, County],
) -> None:
    seller, category, state, primary, extra = generic_reference
    client.force_login(seller.user)
    categories = client.get(
        reverse("listings:generic_categories"), {"vertical": category.vertical_id}
    )
    counties = client.get(
        reverse("listings:generic_county_candidates"),
        {"state": str(state.id), "postal_code": "77001"},
    )
    assert categories.json()["categories"] == [
        {"id": category.id, "name": "Services \u203a Cleaning"}
    ]
    assert {item["id"] for item in counties.json()["counties"]} == {primary.id, extra.id}
    assert counties.json()["status"] == "zip_verified"
    assert all(item["verified"] for item in counties.json()["counties"])
    response = client.post(
        reverse("listings:create_generic_draft"),
        {
            "vertical": category.vertical_id,
            "category": category.id,
            "state": state.id,
            "county": primary.id,
            "additional_counties": [extra.id],
            "city": "Amarillo",
            "title": "Create through form",
            "description": "Private street is not public",
            "price_mode": "contact",
            "postal_code": "77001",
            "street_address": "1 Private Way",
            "currency": "USD",
        },
    )
    assert response.status_code == 302
    detail_url = response["Location"]
    listing_id = detail_url.rsplit("/", 2)[-2]
    detail = client.get(detail_url)
    assert detail.status_code == 200
    assert b"1 Private Way" not in detail.content
    edit = client.post(
        reverse("listings:edit_generic_draft", kwargs={"listing_id": listing_id}),
        {
            "vertical": category.vertical_id,
            "category": category.id,
            "state": state.id,
            "county": primary.id,
            "city": "Amarillo",
            "title": "Edited through form",
            "description": "Updated",
            "price_mode": "free",
            "postal_code": "77001",
            "street_address": "",
            "currency": "",
        },
    )
    assert edit.status_code == 302


def test_generic_county_endpoint_returns_state_counties_before_zip_verification(
    client: Client,
    generic_reference: tuple[SellerProfile, Category, State, County, County],
) -> None:
    seller, _category, state, primary, extra = generic_reference
    unverified = County.objects.create(
        fips="48113", state=state, name="Dallas", slug="dallas", is_active=True
    )
    client.force_login(seller.user)

    counties = client.get(
        reverse("listings:generic_county_candidates"),
        {"state": str(state.id)},
    ).json()

    assert counties["status"] == "state_counties"
    assert {item["id"] for item in counties["counties"]} == {primary.id, extra.id, unverified.id}
    assert not any(item["verified"] for item in counties["counties"])


def test_generic_county_endpoint_reports_missing_crosswalk(
    client: Client,
    generic_reference: tuple[SellerProfile, Category, State, County, County],
) -> None:
    seller, _category, state, _primary, _extra = generic_reference
    ZipCountyReference.objects.all().delete()
    client.force_login(seller.user)

    response = client.get(
        reverse("listings:generic_county_candidates"),
        {"state": str(state.id), "postal_code": "77001"},
    )

    assert response.json() == {
        "counties": [
            {"id": county.id, "name": county.name, "verified": False}
            for county in County.objects.filter(state=state, is_active=True).order_by("name")
        ],
        "status": "zip_no_candidates",
        "crosswalk_loaded": False,
    }


def test_generic_county_endpoint_search_is_bounded_and_state_scoped(
    client: Client,
    generic_reference: tuple[SellerProfile, Category, State, County, County],
) -> None:
    seller, _category, state, _primary, _extra = generic_reference
    alaska = State.objects.create(
        fips="02", usps_code="AK", name="Alaska", slug="alaska", is_active=True
    )
    County.objects.create(
        fips="02020", state=alaska, name="Anchorage", slug="anchorage", is_active=True
    )
    inactive = County.objects.create(
        fips="48113",
        state=state,
        name="Anchorage Inactive",
        slug="anchorage-inactive",
        is_active=False,
    )
    for index in range(25):
        County.objects.create(
            fips=f"48{index:03d}",
            state=state,
            name=f"Searchable {index:02d}",
            slug=f"searchable-{index:02d}",
            is_active=True,
        )
    client.force_login(seller.user)

    response = client.get(
        reverse("listings:generic_county_candidates"), {"state": str(state.id), "q": "searchable"}
    )

    assert response.status_code == 200
    counties = response.json()["counties"]
    assert len(counties) == 20
    assert [county["name"] for county in counties] == sorted(county["name"] for county in counties)
    assert all(county["id"] != inactive.id for county in counties)
    assert all(county["name"] != "Anchorage" for county in counties)
    too_long = client.get(
        reverse("listings:generic_county_candidates"), {"state": str(state.id), "q": "x" * 81}
    ).json()
    assert too_long["status"] == "invalid_query"
    assert too_long["counties"] == []


def test_generic_form_keeps_county_select_fallback_and_rejects_foreign_county(
    client: Client,
    generic_reference: tuple[SellerProfile, Category, State, County, County],
) -> None:
    seller, category, state, primary, _extra = generic_reference
    alaska = State.objects.create(
        fips="02", usps_code="AK", name="Alaska", slug="alaska", is_active=True
    )
    foreign_county = County.objects.create(
        fips="02020", state=alaska, name="Anchorage", slug="anchorage", is_active=True
    )
    client.force_login(seller.user)

    fallback = client.get(reverse("listings:create_generic_draft"))
    rejected = client.post(
        reverse("listings:create_generic_draft"),
        {
            "vertical": category.vertical_id,
            "category": category.id,
            "state": state.id,
            "county": foreign_county.id,
            "city": "Amarillo",
            "title": "Wrong county",
            "description": "This must not save.",
            "price_mode": "contact",
            "postal_code": "77001",
        },
    )

    assert fallback.status_code == 200
    assert b'<select name="county"' in fallback.content
    assert b'<select name="additional_counties"' in fallback.content
    assert b"List on Nearby Counties" in fallback.content
    assert rejected.status_code == 200
    assert b"Select a valid choice" in rejected.content
    assert primary.id != foreign_county.id
