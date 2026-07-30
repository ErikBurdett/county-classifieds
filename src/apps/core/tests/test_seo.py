from __future__ import annotations

import pytest
from django.test import Client
from django.test.utils import override_settings

from apps.locations.models import County, State

pytestmark = pytest.mark.django_db


def test_robots_advertises_sitemap_and_private_paths(client: Client) -> None:
    response = client.get("/robots.txt")

    assert response.status_code == 200
    assert b"Sitemap: http://testserver/sitemap.xml" in response.content
    assert b"Disallow: /dashboard/" in response.content
    assert b"Disallow: /staff/" in response.content


def test_sitemaps_only_include_active_directory_records(client: Client) -> None:
    active = State.objects.create(
        fips="48",
        usps_code="TX",
        name="Texas",
        slug="texas",
        is_active=True,
        is_network_enabled=True,
    )
    County.objects.create(
        fips="48375",
        state=active,
        name="Potter",
        slug="potter",
        is_active=True,
        is_network_enabled=True,
    )
    State.objects.create(
        fips="40",
        usps_code="OK",
        name="Oklahoma",
        slug="oklahoma",
        is_active=False,
        is_network_enabled=False,
    )

    index = client.get("/sitemap.xml")
    states = client.get("/sitemaps/states-1.xml")
    counties = client.get("/sitemaps/counties-1.xml")

    assert index.status_code == 200
    assert b"/sitemaps/listings-1.xml" in b"".join(index)
    assert b"/texas/" in b"".join(states)
    assert b"/oklahoma/" not in b"".join(client.get("/sitemaps/states-1.xml"))
    assert b"/texas/potter/" in b"".join(counties)


def test_filtered_browse_is_noindex_and_canonicalizes_to_path(client: Client) -> None:
    State.objects.create(
        fips="48",
        usps_code="TX",
        name="Texas",
        slug="texas",
        is_active=True,
        is_network_enabled=True,
    )

    response = client.get("/texas/", {"q": "tractor", "page": "2"})

    assert response.status_code == 200
    assert b'<meta name="robots" content="noindex,follow">' in response.content
    assert b'<link rel="canonical" href="http://testserver/texas/">' in response.content


@override_settings(ALLOWED_HOSTS=["social.example"])
def test_public_directory_metadata_uses_clean_absolute_canonical_url(client: Client) -> None:
    State.objects.create(
        fips="48",
        usps_code="TX",
        name="Texas",
        slug="texas",
        is_active=True,
        is_network_enabled=False,
    )

    home = client.get("/", HTTP_HOST="social.example")
    response = client.get(
        "/texas/",
        {"q": "private-query", "page": "2"},
        HTTP_HOST="social.example",
    )

    assert home.status_code == 200
    assert b'<meta property="og:url" content="http://social.example/">' in home.content
    assert b'<meta name="twitter:card" content="summary">' in home.content
    assert response.status_code == 200
    assert b"<title>Listings in Texas | TheCountyPost Market</title>" in response.content
    assert (
        b'<meta name="description" content="Browse public listings in Texas '
        b'on TheCountyPost Market.">' in response.content
    )
    assert b'<meta property="og:url" content="http://social.example/texas/">' in response.content
    assert b'<link rel="canonical" href="http://social.example/texas/">' in response.content
    assert b'<meta property="og:image"' not in response.content
    assert b'<meta name="twitter:card" content="summary">' in response.content


def test_county_equivalent_metadata_uses_imported_display_name(client: Client) -> None:
    maryland = State.objects.create(
        fips="24",
        usps_code="MD",
        name="Maryland",
        slug="maryland",
        is_active=True,
    )
    County.objects.create(
        fips="24510",
        state=maryland,
        name="Baltimore city",
        slug="baltimore-city",
        is_active=True,
    )

    response = client.get("/maryland/baltimore-city/")

    assert response.status_code == 200
    assert b"<title>Listings in Baltimore city, Maryland | TheCountyPost Market</title>" in (
        response.content
    )
    assert b"Browse public listings in Baltimore city, Maryland" in response.content
    assert b"Baltimore city County" not in response.content


@override_settings(DEBUG=False)
def test_not_found_page_is_branded_and_does_not_echo_the_path(client: Client) -> None:
    response = client.get("/missing-private-market/?token=not-for-display")

    assert response.status_code == 404
    assert b"We could not find that market page" in response.content
    assert b"Find a market" in response.content
    assert b"missing-private-market" not in response.content
    assert response.content.count(b"<main") == 1
