from __future__ import annotations

from typing import Protocol

import pytest
from django.core.management import call_command
from django.test.utils import override_settings
from playwright.sync_api import Browser, Page, expect

from apps.accounts.models import SellerProfile, User
from apps.catalog.models import Vertical
from apps.listings.models import Listing
from apps.locations.models import County, State

pytestmark = pytest.mark.e2e


class LiveServer(Protocol):
    url: str


def test_home_page_renders_in_chromium(page: Page, live_server: LiveServer) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{live_server.url}/")

    expect(page).to_have_title("Regional marketplace | TheCountyPost Market")
    expect(
        page.get_by_role("heading", name="A better way to find regional listings")
    ).to_be_visible()
    expect(page.get_by_role("heading", name="Find your market")).to_be_visible()
    expect(page.get_by_text("All active state markets", exact=True)).to_be_visible()
    expect(page.get_by_role("link", name="Skip to main content")).to_be_visible()
    menu_button = page.get_by_role("button", name="Menu")
    expect(menu_button).to_have_attribute("aria-controls", "primary-navigation")
    expect(menu_button).to_have_attribute("aria-expanded", "false")
    menu_button.click()
    expect(menu_button).to_have_attribute("aria-expanded", "true")
    expect(page.get_by_role("link", name="Log in")).to_be_visible()
    page.keyboard.press("Escape")
    expect(menu_button).to_have_attribute("aria-expanded", "false")
    expect(menu_button).to_be_focused()


def test_mobile_navigation_keeps_links_available_without_javascript(
    browser: Browser, live_server: LiveServer
) -> None:
    context = browser.new_context(
        java_script_enabled=False,
        viewport={"width": 390, "height": 844},
    )
    page = context.new_page()
    try:
        page.goto(f"{live_server.url}/")
        expect(page.get_by_role("link", name="Log in")).to_be_visible()
        expect(page.get_by_role("link", name="Register")).to_be_visible()
    finally:
        context.close()


@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_mobile_browse_filters_remain_open_without_javascript(
    browser: Browser, live_server: LiveServer
) -> None:
    call_command("seed_demo_marketplace", verbosity=0)
    context = browser.new_context(
        java_script_enabled=False,
        viewport={"width": 390, "height": 844},
    )
    page = context.new_page()
    try:
        page.goto(f"{live_server.url}/texas/potter/")
        expect(page.get_by_role("textbox", name="Search listings")).to_be_visible()
        expect(page.get_by_role("button", name="Apply filters")).to_be_visible()
    finally:
        context.close()


@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_seeded_generic_taxonomy_listing_searches_and_displays_public_details(
    page: Page, live_server: LiveServer
) -> None:
    call_command("seed_demo_marketplace", verbosity=0)
    call_command("seed_marketplace_catalog", verbosity=0)
    call_command("seed_demo_generic_taxonomy", verbosity=0)
    listing = Listing.objects.get(title__startswith="Synthetic taxonomy fixture: services")

    page.goto(
        f"{live_server.url}/{listing.state.slug}/{listing.county.slug}/?q=directory-service-demo"
    )
    listing_link = page.get_by_role("link", name=listing.title)
    expect(listing_link).to_be_visible()
    listing_link.click()

    expect(page.get_by_role("heading", name="Tags")).to_be_visible()
    expect(page.get_by_text("directory-service-demo", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Additional details")).to_be_visible()
    expect(page.get_by_text("Weekday demonstration", exact=True)).to_be_visible()


@pytest.mark.django_db(transaction=True)
def test_authenticated_mobile_navigation_keeps_create_listing_available(
    page: Page, live_server: LiveServer
) -> None:
    user = User.objects.create_user(email="mobile-seller@example.com", password="test-password")
    SellerProfile.objects.create(user=user, display_name="Mobile seller")
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{live_server.url}/login/")
    page.get_by_label("Email").fill(user.email)
    page.get_by_label("Password").fill("test-password")
    page.get_by_role("button", name="Sign in").click()

    expect(page.get_by_role("banner").get_by_role("link", name="Create listing")).to_be_visible()
    assert page.locator("body").evaluate("(element) => element.scrollWidth <= window.innerWidth")


@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_seller_dashboard_actions_stack_at_mobile_width(
    page: Page, live_server: LiveServer
) -> None:
    call_command("seed_demo_marketplace", verbosity=0)
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{live_server.url}/login/")
    page.get_by_label("Email").fill("telephoneheater@local.test")
    page.get_by_label("Password").fill("LocalDemoOnly-ChangeMe-2026!")
    page.get_by_role("button", name="Sign in").click()
    page.goto(f"{live_server.url}/dashboard/")

    expect(
        page.get_by_label("Your listings").get_by_role("link", name="Create listing")
    ).to_be_visible()
    expect(page.get_by_role("group", name="Actions for 2023 Demo TX Auto 1")).to_be_visible()
    expect(page.get_by_role("button", name="Mark sold").first).to_be_visible()
    assert page.locator("body").evaluate("(element) => element.scrollWidth <= window.innerWidth")


@pytest.mark.django_db
def test_location_placeholder_renders_in_chromium(page: Page, live_server: LiveServer) -> None:
    texas = State.objects.create(
        fips="48",
        usps_code="TX",
        name="Texas",
        slug="texas",
        is_active=True,
        is_network_enabled=True,
    )
    County.objects.create(
        fips="48375",
        state=texas,
        name="Potter",
        slug="potter",
        is_active=True,
        is_network_enabled=True,
    )

    page.goto(f"{live_server.url}/TEXAS/POTTER/")

    expect(page).to_have_url(f"{live_server.url}/texas/potter/")
    expect(page.get_by_role("heading", name="Listings in Potter, Texas")).to_be_visible()


@pytest.mark.django_db
def test_market_finder_searches_active_counties_in_chromium(
    page: Page, live_server: LiveServer
) -> None:
    texas = State.objects.create(
        fips="48",
        usps_code="TX",
        name="Texas",
        slug="texas",
        is_active=True,
        is_network_enabled=True,
    )
    County.objects.create(
        fips="48375",
        state=texas,
        name="Potter",
        slug="potter",
        is_active=True,
        is_network_enabled=True,
    )
    County.objects.create(
        fips="48113",
        state=texas,
        name="Inactive Potter",
        slug="inactive-potter",
        is_active=False,
        is_network_enabled=False,
    )

    page.goto(f"{live_server.url}/")
    page.get_by_role("textbox", name="Search state or county").fill("Potter")

    expect(page).to_have_url(f"{live_server.url}/markets/?q=Potter")
    expect(page.get_by_role("heading", name="Matching markets")).to_be_visible()
    expect(page.get_by_role("status")).to_be_attached()
    expect(page.get_by_text("Inactive Potter", exact=False)).not_to_be_attached()
    page.get_by_role("link", name="Potter, TX").click()
    expect(page).to_have_url(f"{live_server.url}/texas/potter/")


@pytest.mark.django_db
def test_state_market_finder_searches_live_results_in_chromium(
    page: Page, live_server: LiveServer
) -> None:
    texas = State.objects.create(
        fips="48",
        usps_code="TX",
        name="Texas",
        slug="texas",
        is_active=True,
        is_network_enabled=True,
    )
    County.objects.create(
        fips="48375",
        state=texas,
        name="Potter",
        slug="potter",
        is_active=True,
        is_network_enabled=True,
    )

    page.goto(f"{live_server.url}/texas/")
    page.get_by_role("textbox", name="Search state or county").fill("Potter")

    expect(page).to_have_url(f"{live_server.url}/markets/?q=Potter")
    expect(page.get_by_role("heading", name="Matching markets")).to_be_visible()
    expect(page.get_by_role("link", name="Potter, TX")).to_be_visible()


@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_seeded_county_browse_renders_in_chromium(page: Page, live_server: LiveServer) -> None:
    call_command("seed_demo_marketplace", verbosity=0)

    page.goto(f"{live_server.url}/texas/potter/")

    expect(page.get_by_role("heading", name="Listings in Potter, Texas")).to_be_visible()
    expect(page.get_by_role("heading", name="2023 Demo TX Auto 1")).to_be_visible()


@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_seeded_listing_detail_renders_google_map_frame_in_chromium(
    page: Page, live_server: LiveServer
) -> None:
    call_command("seed_demo_marketplace", verbosity=0)
    listing = Listing.objects.get(title="2023 Demo TX Auto 1")

    page.goto(f"{live_server.url}/texas/potter/listing/{listing.id}/")

    expect(page.locator(".listing-map-frame iframe")).to_be_attached()


@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_browse_filters_update_live_results_in_chromium(
    page: Page, live_server: LiveServer
) -> None:
    call_command("seed_demo_marketplace", verbosity=0)

    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{live_server.url}/texas/potter/")
    filter_toggle = page.get_by_role("button", name="Show filters")
    expect(filter_toggle).to_have_attribute("aria-expanded", "false")
    filter_toggle.click()
    filter_toggle = page.get_by_role("button", name="Hide filters")
    expect(filter_toggle).to_have_attribute("aria-expanded", "true")
    page.keyboard.press("Escape")
    filter_toggle = page.get_by_role("button", name="Show filters")
    expect(filter_toggle).to_have_attribute("aria-expanded", "false")
    expect(filter_toggle).to_be_focused()
    filter_toggle.click()
    query = page.locator('form[data-live-search="browse"] input[name="q"]')
    query.fill("2023 Demo TX Auto 1")

    expect(page.get_by_role("region", name="Listing search results")).to_contain_text(
        "2023 Demo TX Auto 1"
    )
    expect(page).to_have_url(f"{live_server.url}/texas/potter/?q=2023+Demo+TX+Auto+1&sort=newest")
    page.get_by_role("combobox", name="Sort").select_option("price_asc")
    expect(page).to_have_url(
        f"{live_server.url}/texas/potter/?q=2023+Demo+TX+Auto+1&sort=price_asc"
    )
    assert page.locator("body").evaluate("(element) => element.scrollWidth <= window.innerWidth")


@pytest.mark.django_db(transaction=True)
def test_typed_browse_filter_groups_fit_mobile_width(page: Page, live_server: LiveServer) -> None:
    state = State.objects.create(
        fips="48",
        usps_code="TX",
        name="Texas",
        slug="texas",
        is_active=True,
        is_network_enabled=True,
    )
    County.objects.create(
        fips="48375",
        state=state,
        name="Potter",
        slug="potter",
        is_active=True,
        is_network_enabled=True,
    )
    verticals = {
        slug: Vertical.objects.create(name=name, slug=slug)
        for slug, name in (
            ("real-estate", "Real Estate"),
            ("rentals", "Rentals"),
            ("farm-ranch", "Farm & Ranch"),
            ("home-garden", "Home & Garden"),
        )
    }
    page.set_viewport_size({"width": 390, "height": 844})

    for vertical, field_label in (
        (verticals["real-estate"], "Property type"),
        (verticals["rentals"], "Rental type"),
        (verticals["farm-ranch"], "Equipment type"),
        (verticals["home-garden"], "Item type"),
    ):
        page.goto(f"{live_server.url}/texas/potter/?vertical={vertical.id}")
        expect(page.get_by_role("group", name="Listing details")).to_be_visible()
        expect(page.get_by_label(field_label)).to_be_visible()
        assert page.locator("body").evaluate(
            "(element) => element.scrollWidth <= window.innerWidth"
        )


@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_mobile_filter_chips_and_reset_preserve_nearby_radius_in_chromium(
    page: Page, live_server: LiveServer
) -> None:
    call_command("seed_demo_marketplace", verbosity=0)

    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{live_server.url}/texas/potter/?q=2023&nearby_radius=250")

    expect(page.get_by_role("button", name="Hide filters")).to_have_attribute(
        "aria-expanded", "true"
    )
    expect(page.get_by_role("navigation", name="Active filters")).to_contain_text("Search: 2023")
    page.get_by_role("link", name="Remove Search: 2023").click()
    expect(page).to_have_url(f"{live_server.url}/texas/potter/?nearby_radius=250")

    page.goto(f"{live_server.url}/texas/potter/?q=2023&nearby_radius=250")
    page.get_by_role("link", name="Reset filters").click()
    expect(page).to_have_url(f"{live_server.url}/texas/potter/?nearby_radius=250")
    assert page.locator("body").evaluate("(element) => element.scrollWidth <= window.innerWidth")


@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_county_nearby_radius_slider_has_get_filter_path_in_chromium(
    page: Page, live_server: LiveServer
) -> None:
    call_command("seed_demo_marketplace", verbosity=0)

    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{live_server.url}/texas/potter/")
    page.get_by_role("button", name="Show filters").click()
    slider = page.get_by_role("slider", name="Nearby county distance")
    slider.evaluate(
        """
        (element) => {
          element.value = "250";
          element.dispatchEvent(new Event("input", { bubbles: true }));
          element.dispatchEvent(new Event("change", { bubbles: true }));
        }
        """
    )

    expect(page.get_by_text("250 miles", exact=True)).to_be_visible()
    expect(page).to_have_url(f"{live_server.url}/texas/potter/?sort=newest&nearby_radius=250")
    assert page.locator("body").evaluate("(element) => element.scrollWidth <= window.innerWidth")
