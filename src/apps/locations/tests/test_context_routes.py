from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import SellerProfile, User
from apps.catalog.models import Category, Vertical
from apps.listings.models import AutoDetails, Listing, ListingCountyPlacement, ListingStatus
from apps.locations.models import County, State

pytestmark = pytest.mark.django_db


@pytest.fixture
def texas_and_potter() -> tuple[State, County]:
    texas = State.objects.create(
        fips="48",
        usps_code="TX",
        name="Texas",
        slug="texas",
        is_active=True,
        is_network_enabled=True,
    )
    potter = County.objects.create(
        fips="48375",
        state=texas,
        name="Potter",
        slug="potter",
        is_active=True,
        is_network_enabled=True,
    )
    return texas, potter


def test_active_context_routes_render_indexable_directory(
    client: Client, texas_and_potter: tuple[State, County]
) -> None:
    state_response = client.get("/texas/")
    county_response = client.get("/texas/potter/")

    assert state_response.status_code == 200
    assert county_response.status_code == 200
    assert b'<meta name="robots" content="noindex">' not in county_response.content
    assert b"This county route starts with statewide results." in county_response.content


def test_uppercase_context_routes_redirect_to_lowercase(
    client: Client, texas_and_potter: tuple[State, County]
) -> None:
    response = client.get("/TEXAS/POTTER/?ref=header")

    assert response.status_code == 301
    assert (
        response["Location"]
        == reverse(
            "locations:county_context",
            kwargs={"state_slug": "texas", "county_slug": "potter"},
        )
        + "?ref=header"
    )


@pytest.mark.parametrize(
    ("state_active", "state_network_enabled", "county_active", "county_network_enabled"),
    [
        (False, False, True, True),
        (True, False, False, False),
    ],
)
def test_inactive_context_routes_return_404(
    client: Client,
    state_active: bool,
    state_network_enabled: bool,
    county_active: bool,
    county_network_enabled: bool,
) -> None:
    texas = State.objects.create(
        fips="48",
        usps_code="TX",
        name="Texas",
        slug="texas",
        is_active=state_active,
        is_network_enabled=state_network_enabled,
    )
    County.objects.create(
        fips="48375",
        state=texas,
        name="Potter",
        slug="potter",
        is_active=county_active,
        is_network_enabled=county_network_enabled,
    )

    assert client.get("/texas/potter/").status_code == 404


def test_unknown_context_routes_return_404(client: Client) -> None:
    assert client.get("/unknown/").status_code == 404
    assert client.get("/texas/unknown/").status_code == 404


def test_market_finder_returns_active_text_search_results(
    client: Client, texas_and_potter: tuple[State, County]
) -> None:
    texas, potter = texas_and_potter

    response = client.get("/markets/", {"q": "Texas"})

    assert response.status_code == 200
    assert texas.name.encode() in response.content
    assert potter.name.encode() in response.content
    assert b"/texas/potter/" in response.content


def test_market_finder_fragment_returns_only_live_result_region(
    client: Client, texas_and_potter: tuple[State, County]
) -> None:
    response = client.get(
        "/markets/",
        {"q": "Potter"},
        headers={"Accept": "text/vnd.countypost.fragment+html"},
    )

    assert response.status_code == 200
    assert b'id="market-finder-results"' in response.content
    assert b"Potter, TX" in response.content
    assert b"<html" not in response.content
    assert "Accept" in response["Vary"]


def test_state_market_finder_has_live_results_and_local_markets_follow_listings(
    client: Client, texas_and_potter: tuple[State, County]
) -> None:
    response = client.get("/texas/")

    assert response.status_code == 200
    content = response.content
    assert b'id="market-finder-results"' in content
    assert content.index(b'id="listings-title"') < content.index(b'id="counties-title"')


def test_blank_market_finder_query_keeps_full_page_get_fallback(client: Client) -> None:
    response = client.get("/markets/")

    assert response.status_code == 200
    assert b'<form class="market-finder-form" method="get"' in response.content
    assert b"Search markets</button>" in response.content


def test_invalid_browse_fragment_returns_safe_error_status(
    client: Client, texas_and_potter: tuple[State, County]
) -> None:
    response = client.get(
        "/texas/potter/",
        {"min_price": "not-a-price"},
        headers={"Accept": "text/vnd.countypost.fragment+html"},
    )

    assert response.status_code == 400
    assert b'id="listing-results"' in response.content
    assert b"not-a-price" not in response.content


def test_browse_filter_chips_only_use_validated_allowlisted_values(
    client: Client, texas_and_potter: tuple[State, County]
) -> None:
    texas, _potter = texas_and_potter
    autos = Vertical.objects.create(name="Autos", slug="autos")
    cars = Category.objects.create(vertical=autos, name="Cars", slug="cars")

    query: dict[str, str] = {
        "q": "truck",
        "vertical": str(autos.pk),
        "category": str(cars.pk),
        "min_price": "12000",
        "sort": "price_asc",
        "untrusted": "never-copy-this",
        "page": "4",
    }
    response = client.get(
        "/texas/",
        query,
    )

    assert response.status_code == 200
    content = response.content.decode()
    expected_query = (
        f"vertical={autos.pk}&amp;category={cars.pk}&amp;min_price=12000&amp;sort=price_asc"
    )
    assert f'href="/texas/?{expected_query}"' in content
    assert "untrusted" not in content
    assert "page=4" not in content
    assert response.context["pagination_query"] == (
        f"q=truck&vertical={autos.pk}&category={cars.pk}&min_price=12000&sort=price_asc"
    )
    assert texas.name in content


def test_invalid_browse_filters_open_disclosure_and_keep_only_valid_filter_chips(
    client: Client, texas_and_potter: tuple[State, County]
) -> None:
    response = client.get(
        "/texas/potter/",
        {"q": "truck", "min_price": "not-a-price", "untrusted": "never-copy-this"},
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert 'data-filter-open="true"' in content
    assert 'data-filter-has-errors="true"' in content
    assert 'href="/texas/potter/" aria-label="Remove Search: truck"' in content
    assert "untrusted" not in content


def test_county_scope_is_explicit_safe_and_includes_additional_placements(
    client: Client, texas_and_potter: tuple[State, County]
) -> None:
    texas, potter = texas_and_potter
    autos = Vertical.objects.create(name="Autos", slug="autos")
    category = Category.objects.create(vertical=autos, name="Cars", slug="cars")
    seller = SellerProfile.objects.create(
        user=User.objects.create_user(email="scope@example.test", password="not-used"),
        display_name="Scope seller",
    )
    other = County.objects.create(
        fips="48421",
        state=texas,
        name="Sherman",
        slug="sherman",
        is_active=True,
        is_network_enabled=True,
    )
    listing = Listing.objects.create(
        seller=seller,
        vertical=autos,
        category=category,
        state=texas,
        county=potter,
        city="Amarillo",
        title="Statewide tractor",
        description="Public result",
        status=ListingStatus.PUBLISHED,
        published_at=timezone.now(),
    )
    AutoDetails.objects.create(
        listing=listing,
        vehicle_type="truck",
        year=2020,
        make="Ford",
        model="Ranger",
        mileage=1,
        title_status="clean",
    )
    ListingCountyPlacement.objects.create(listing=listing, county=other)

    default_response = client.get("/texas/sherman/")
    county_response = client.get("/texas/sherman/", {"scope": "county"})
    invalid_response = client.get("/texas/sherman/", {"scope": "unsafe"})

    assert (
        default_response.status_code
        == county_response.status_code
        == invalid_response.status_code
        == 200
    )
    assert b"Statewide tractor" in county_response.content
    assert b"scope=county" in county_response.content
    assert b"unsafe" not in invalid_response.content


def test_market_finder_excludes_inactive_locations(
    client: Client, texas_and_potter: tuple[State, County]
) -> None:
    _texas, potter = texas_and_potter
    potter.is_active = False
    potter.save(update_fields=("is_active",))

    response = client.get("/markets/", {"q": "Potter"})

    assert response.status_code == 200
    assert b"No active counties matched." in response.content


def test_network_disabled_but_active_context_routes_and_directory_results_remain_visible(
    client: Client, texas_and_potter: tuple[State, County]
) -> None:
    _texas, potter = texas_and_potter
    potter.is_network_enabled = False
    potter.save(update_fields=("is_network_enabled",))

    route_response = client.get("/texas/potter/")
    finder_response = client.get("/markets/", {"q": "Potter"})

    assert route_response.status_code == 200
    assert b"Potter, TX" in finder_response.content
