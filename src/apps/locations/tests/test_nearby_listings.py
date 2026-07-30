from __future__ import annotations

from decimal import Decimal

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import SellerProfile, User
from apps.catalog.models import Category, Vertical
from apps.listings.models import GenericListingDetails, Listing, ListingStatus
from apps.listings.selectors import public_listings_near_county
from apps.locations.forms import PublicBrowseForm
from apps.locations.models import County, State

pytestmark = pytest.mark.django_db


@pytest.fixture
def nearby_market() -> tuple[County, County, County, Listing, Listing]:
    vertical = Vertical.objects.create(name="Autos", slug="autos")
    category = Category.objects.create(vertical=vertical, name="Cars", slug="cars")
    origin_state = State.objects.create(
        fips="48",
        usps_code="TX",
        name="Texas",
        slug="texas",
        is_active=True,
        is_network_enabled=True,
    )
    nearby_state = State.objects.create(
        fips="40",
        usps_code="OK",
        name="Oklahoma",
        slug="oklahoma",
        is_active=True,
        is_network_enabled=True,
    )
    origin = County.objects.create(
        fips="48375",
        state=origin_state,
        name="Origin",
        slug="origin",
        centroid_latitude=Decimal("0"),
        centroid_longitude=Decimal("0"),
        is_active=True,
        is_network_enabled=True,
    )
    nearby = County.objects.create(
        fips="40143",
        state=nearby_state,
        name="Nearby",
        slug="nearby",
        centroid_latitude=Decimal("0"),
        centroid_longitude=Decimal("0.5"),
        is_active=True,
        is_network_enabled=True,
    )
    far = County.objects.create(
        fips="40109",
        state=nearby_state,
        name="Far",
        slug="far",
        centroid_latitude=Decimal("0"),
        centroid_longitude=Decimal("5"),
        is_active=True,
        is_network_enabled=True,
    )
    seller = SellerProfile.objects.create(
        user=User.objects.create_user(email="nearby@example.test", password="not-used"),
        display_name="Nearby seller",
    )

    def listing(*, county: County, title: str, status: str = ListingStatus.PUBLISHED) -> Listing:
        created_listing = Listing.objects.create(
            seller=seller,
            vertical=vertical,
            category=category,
            state=county.state,
            county=county,
            city=county.name,
            title=title,
            description="Public listing description",
            price_minor=100,
            currency="USD",
            status=status,
            published_at=timezone.now() if status == ListingStatus.PUBLISHED else None,
        )
        GenericListingDetails.objects.create(
            listing=created_listing,
            price_mode="fixed",
            postal_code="00000",
        )
        return created_listing

    near_listing = listing(county=nearby, title="Nearby public listing")
    listing(county=origin, title="Current county listing")
    listing(county=nearby, title="Private draft", status=ListingStatus.DRAFT)
    return origin, nearby, far, near_listing, listing(county=far, title="Far public listing")


def test_nearby_selector_filters_distance_county_and_public_visibility(
    nearby_market: tuple[County, County, County, Listing, Listing],
) -> None:
    origin, _nearby, _far, near_listing, far_listing = nearby_market

    nearby = list(public_listings_near_county(county=origin, radius_miles=50))

    assert [listing.id for listing in nearby] == [near_listing.id]
    assert not public_listings_near_county(county=origin, radius_miles=10).exists()
    assert far_listing.id not in {
        listing.id for listing in public_listings_near_county(county=origin, radius_miles=250)
    }


def test_nearby_selector_returns_empty_when_origin_coordinates_are_missing(
    nearby_market: tuple[County, County, County, Listing, Listing],
) -> None:
    origin, _nearby, _far, _near_listing, _far_listing = nearby_market
    origin.centroid_latitude = None
    origin.centroid_longitude = None
    origin.save(update_fields=("centroid_latitude", "centroid_longitude"))

    assert not public_listings_near_county(county=origin, radius_miles=50).exists()


def test_nearby_radius_form_requires_ten_mile_steps(
    nearby_market: tuple[County, County, County, Listing, Listing],
) -> None:
    origin, _nearby, _far, _near_listing, _far_listing = nearby_market

    form = PublicBrowseForm({"nearby_radius": "255"}, state=origin.state, fixed_county=origin)
    assert not form.is_valid()
    assert "nearby_radius" in form.errors

    stepped_form = PublicBrowseForm(
        {"nearby_radius": "55"}, state=origin.state, fixed_county=origin
    )
    assert not stepped_form.is_valid()
    assert "10-mile increments" in str(stepped_form.errors["nearby_radius"])


def test_county_page_renders_nearby_rail_without_private_or_current_county_rows(
    client: Client,
    nearby_market: tuple[County, County, County, Listing, Listing],
) -> None:
    _origin, _nearby, _far, _near_listing, _far_listing = nearby_market

    response = client.get("/texas/origin/", {"nearby_radius": "50"})

    assert response.status_code == 200
    assert b"Nearby counties" in response.content
    assert b"Nearby public listing" in response.content
    assert b"Current county listing" in response.content
    assert b"Private draft" not in response.content
    assert b"About 35 miles away" in response.content
    assert b"noindex,follow" in response.content


def test_county_page_omits_nearby_rail_without_centroid(
    client: Client,
    nearby_market: tuple[County, County, County, Listing, Listing],
) -> None:
    origin, _nearby, _far, _near_listing, _far_listing = nearby_market
    origin.centroid_latitude = None
    origin.centroid_longitude = None
    origin.save(update_fields=("centroid_latitude", "centroid_longitude"))

    response = client.get("/texas/origin/")

    assert response.status_code == 200
    assert b"Nearby counties" not in response.content
