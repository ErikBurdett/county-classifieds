from __future__ import annotations

from typing import Protocol

import pytest
from playwright.sync_api import Page, expect

from apps.accounts.models import SellerProfile, User
from apps.catalog.models import CatalogPostingField, CatalogPostingProfile, Category, Vertical
from apps.listings.models import GenericListingDetails, HomeDetails, Listing
from apps.locations.models import County, State, ZipCountyReference

pytestmark = pytest.mark.e2e


class LiveServer(Protocol):
    url: str


def _expect_no_validation_errors(page: Page) -> None:
    expect(page.locator("[data-error-summary]")).to_have_count(0)
    expect(page.get_by_text("This field is required.")).to_have_count(0)


@pytest.mark.django_db(transaction=True)
def test_generic_county_search_selects_an_alaska_county_with_keyboard(
    page: Page, live_server: LiveServer
) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    user = User.objects.create_user(email="seller@example.com", password="test-password")
    SellerProfile.objects.create(user=user, display_name="Seller")
    vertical = Vertical.objects.create(name="Services", slug="services")
    Category.objects.create(vertical=vertical, name="Cleaning", slug="cleaning")
    alaska = State.objects.create(
        fips="02", usps_code="AK", name="Alaska", slug="alaska", is_active=True
    )
    anchorage = County.objects.create(
        fips="02020", state=alaska, name="Anchorage", slug="anchorage", is_active=True
    )
    matanuska = County.objects.create(
        fips="02170",
        state=alaska,
        name="Matanuska-Susitna",
        slug="matanuska-susitna",
        is_active=True,
    )
    for county in (anchorage, matanuska):
        ZipCountyReference.objects.create(
            postal_code="99501",
            county=county,
            source_name="test",
            source_url="https://example.test/crosswalk",
            release_version="test",
            release_date="2026-07-24",
            sha256_checksum="0" * 64,
            transformation_version="test",
        )

    page.goto(f"{live_server.url}/login/")
    page.get_by_label("Email").fill("seller@example.com")
    page.get_by_label("Password").fill("test-password")
    page.get_by_role("button", name="Sign in").click()
    page.goto(f"{live_server.url}/dashboard/listings/new/")
    assert page.locator("body").evaluate("(element) => element.scrollWidth <= window.innerWidth")
    state_search = page.get_by_role("combobox", name="Search state or territory")
    state_search.fill("Alas")
    expect(page.locator("[data-state-results] [role='option']", has_text="Alaska")).to_be_visible()
    state_search.press("ArrowDown")
    state_search.press("Enter")
    expect(page.locator("#id_state")).to_have_value(str(alaska.id))
    county_search = page.get_by_role("combobox", name="Search primary county")
    expect(county_search).to_be_enabled()
    county_search.fill("Anch")
    expect(
        page.locator("[data-county-results] [role='option']", has_text="Anchorage")
    ).to_be_visible()
    county_search.press("ArrowDown")
    county_search.press("Enter")
    expect(county_search).to_have_value("Anchorage")
    expect(page.locator("#id_county")).to_have_value(str(anchorage.id))
    expect(page.locator("[data-county-fallback]")).to_be_hidden()
    page.get_by_label("Postal / ZIP code").fill("99501")
    page.get_by_label("Postal / ZIP code").press("Tab")
    expect(page.get_by_role("status")).to_contain_text("Anchorage: Verified for this ZIP")
    nearby_search = page.get_by_role("combobox", name="Search nearby counties")
    nearby_search.fill("Matanuska")
    expect(
        page.locator(
            "[data-additional-county-results] [role='option']", has_text="Matanuska-Susitna"
        )
    ).to_be_visible()
    nearby_search.press("ArrowDown")
    nearby_search.press("Enter")
    expect(page.get_by_role("list", name="Selected nearby counties")).to_contain_text(
        "Matanuska-Susitna — Verified for this ZIP"
    )
    expect(page.locator("#id_additional_counties")).to_have_values([str(matanuska.id)])
    expect(page.locator("[data-placement-quote]")).to_contain_text(
        "$10 primary placement + $5 \u00d7 1 nearby county = $15"
    )
    nearby_search.fill("Anchorage")
    expect(
        page.locator("[data-additional-county-results] [role='option']", has_text="Anchorage")
    ).to_be_visible()
    nearby_search.press("ArrowDown")
    nearby_search.press("Enter")
    expect(page.get_by_role("status")).to_contain_text(
        "Anchorage is already selected or is the primary county."
    )
    expect(page.locator("#id_additional_counties")).to_have_values([str(matanuska.id)])
    page.get_by_role("button", name="Remove Matanuska-Susitna from nearby counties").click()
    expect(page.locator("#id_additional_counties")).to_have_values([])
    assert page.locator("body").evaluate("(element) => element.scrollWidth <= window.innerWidth")


@pytest.mark.django_db(transaction=True)
def test_unified_typed_location_search_uses_keyboard_at_mobile_width(
    page: Page, live_server: LiveServer
) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    user = User.objects.create_user(email="typed-location@example.com", password="test-password")
    SellerProfile.objects.create(user=user, display_name="Typed location seller")
    state = State.objects.create(
        fips="02", usps_code="AK", name="Alaska", slug="alaska", is_active=True
    )
    county = County.objects.create(
        fips="02020", state=state, name="Anchorage", slug="anchorage", is_active=True
    )
    vertical = Vertical.objects.create(name="Real Estate", slug="real-estate")
    category = Category.objects.create(vertical=vertical, name="Homes", slug="homes")

    page.goto(f"{live_server.url}/login/")
    page.get_by_label("Email").fill(user.email)
    page.get_by_label("Password").fill("test-password")
    page.get_by_role("button", name="Sign in").click()
    page.goto(f"{live_server.url}/dashboard/listings/new/")
    page.get_by_label("Vertical").select_option(str(vertical.id))
    page.get_by_label("Category").select_option(str(category.id))
    state_search = page.get_by_role("combobox", name="Search state or territory")
    state_search.fill("Alas")
    expect(page.locator("[data-state-results] [role='option']", has_text="Alaska")).to_be_visible()
    state_search.press("ArrowDown")
    state_search.press("Enter")
    county_search = page.get_by_role("combobox", name="Search county")
    county_search.fill("Anch")
    expect(
        page.locator("[data-county-results] [role='option']", has_text="Anchorage")
    ).to_be_visible()
    county_search.press("ArrowDown")
    county_search.press("Enter")
    expect(page.locator("#id_state")).to_have_value(str(state.id))
    expect(page.locator("#id_county")).to_have_value(str(county.id))
    assert page.locator("body").evaluate("(element) => element.scrollWidth <= window.innerWidth")


@pytest.mark.django_db(transaction=True)
def test_unified_home_and_catalog_profile_flows_at_mobile_width(
    page: Page, live_server: LiveServer
) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    user = User.objects.create_user(email="unified-browser@example.com", password="test-password")
    SellerProfile.objects.create(user=user, display_name="Unified browser seller")
    state = State.objects.create(
        fips="48", usps_code="TX", name="Texas", slug="texas", is_active=True
    )
    county = County.objects.create(
        fips="48375", state=state, name="Potter", slug="potter", is_active=True
    )
    ZipCountyReference.objects.create(
        postal_code="79101",
        county=county,
        source_name="test",
        source_url="https://example.test",
        release_version="test",
        release_date="2026-07-29",
        sha256_checksum="0" * 64,
        transformation_version="test",
    )
    homes = Vertical.objects.create(name="Real Estate", slug="real-estate")
    home_category = Category.objects.create(vertical=homes, name="Homes", slug="homes")
    services = Vertical.objects.create(name="Services", slug="services")
    service_group = Category.objects.create(
        vertical=services, name="Home Services", slug="home-services"
    )
    service_category = Category.objects.create(
        vertical=services, parent=service_group, name="Cleaning", slug="cleaning"
    )
    profile = CatalogPostingProfile.objects.create(category=service_category)
    CatalogPostingField.objects.create(
        profile=profile,
        key="availability",
        label="Availability",
        field_type="choice",
        required=True,
        choices=["weekdays", "weekends"],
    )
    collectibles = Vertical.objects.create(name="Collectibles & Art", slug="collectibles-art")
    collectibles_group = Category.objects.create(vertical=collectibles, name="Art", slug="art")
    collectible_category = Category.objects.create(
        vertical=collectibles,
        parent=collectibles_group,
        name="Paintings & Prints",
        slug="paintings-prints",
    )
    collectible_profile = CatalogPostingProfile.objects.create(category=collectible_category)
    CatalogPostingField.objects.create(
        profile=collectible_profile,
        key="maker_or_creator",
        label="Maker or creator",
        field_type="text",
        maximum=120,
    )

    page.goto(f"{live_server.url}/login/")
    page.get_by_label("Email").fill(user.email)
    page.get_by_label("Password").fill("test-password")
    page.get_by_role("button", name="Sign in").click()
    page.goto(f"{live_server.url}/dashboard/listings/new/")
    page.get_by_label("Vertical").select_option(str(homes.id))
    page.get_by_label("Title").fill("Preserved mobile home")
    page.get_by_label("Description").fill("Preserved before choosing a category.")
    page.get_by_label("Price mode").select_option("fixed")
    page.get_by_label("Asking price (USD)").fill("250000.00")
    page.get_by_label("Category").select_option(str(home_category.id))
    expect(page.get_by_label("Property type")).to_be_visible()
    _expect_no_validation_errors(page)
    expect(page.get_by_label("Broker or brokerage")).to_be_visible()
    expect(page.get_by_label("Title")).to_have_value("Preserved mobile home")
    expect(page.get_by_label("Price minor")).to_have_value("25000000")
    assert page.locator("body").evaluate("(element) => element.scrollWidth <= window.innerWidth")

    page.goto(f"{live_server.url}/dashboard/listings/new/")
    page.get_by_label("Vertical").select_option(str(services.id))
    expect(page.locator(f"#id_category option[value='{service_group.id}']")).to_have_count(0)
    expect(page.get_by_label("Category")).to_contain_text(
        "Services \u203a Home Services \u203a Cleaning"
    )
    page.get_by_label("Category").select_option(str(service_category.id))
    page.get_by_role("button", name="Save listing draft").click()
    expect(page.get_by_label("Availability")).to_be_visible()
    expect(page.get_by_label("Broker or brokerage")).not_to_be_attached()

    page.goto(f"{live_server.url}/dashboard/listings/new/")
    page.get_by_label("Vertical").select_option(str(collectibles.id))
    expect(page.get_by_label("Category")).to_contain_text(
        "Collectibles & Art \u203a Art \u203a Paintings & Prints"
    )
    page.get_by_label("Category").select_option(str(collectible_category.id))
    page.get_by_role("button", name="Save listing draft").click()
    expect(page.get_by_label("Maker or creator")).to_be_visible()
    assert page.locator("body").evaluate("(element) => element.scrollWidth <= window.innerWidth")


@pytest.mark.django_db(transaction=True)
def test_unified_others_automatically_uses_general_and_requires_visible_tag_at_mobile_width(
    page: Page, live_server: LiveServer
) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    user = User.objects.create_user(email="others-browser@example.com", password="test-password")
    SellerProfile.objects.create(user=user, display_name="Others browser seller")
    others = Vertical.objects.create(name="Others", slug="others")
    Category.objects.create(vertical=others, name="General", slug="general")

    page.goto(f"{live_server.url}/login/")
    page.get_by_label("Email").fill(user.email)
    page.get_by_label("Password").fill("test-password")
    page.get_by_role("button", name="Sign in").click()
    page.goto(f"{live_server.url}/dashboard/listings/new/")
    page.get_by_label("Vertical").select_option(str(others.id))

    expect(page.get_by_label("Seller tag 1", exact=True)).to_be_visible()
    expect(
        page.get_by_text("Add at least one plain-text tag to classify this Others listing.")
    ).to_be_visible()
    expect(page.get_by_label("Category")).not_to_be_attached()
    assert page.locator("body").evaluate("(element) => element.scrollWidth <= window.innerWidth")


@pytest.mark.django_db(transaction=True)
def test_unified_home_and_catalog_edits_at_mobile_width(
    page: Page, live_server: LiveServer
) -> None:  # pragma: no cover - exercised by the separate Playwright target
    page.set_viewport_size({"width": 390, "height": 844})
    user = User.objects.create_user(email="edit-browser@example.com", password="test-password")
    seller = SellerProfile.objects.create(user=user, display_name="Edit browser seller")
    state = State.objects.create(
        fips="48", usps_code="TX", name="Texas", slug="texas", is_active=True
    )
    county = County.objects.create(
        fips="48375", state=state, name="Potter", slug="potter", is_active=True
    )
    ZipCountyReference.objects.create(
        postal_code="79101",
        county=county,
        source_name="test",
        source_url="https://example.test",
        release_version="test",
        release_date="2026-07-30",
        sha256_checksum="0" * 64,
        transformation_version="test",
    )
    homes = Vertical.objects.create(name="Real Estate", slug="real-estate")
    home_category = Category.objects.create(vertical=homes, name="Homes", slug="homes")
    home = Listing.objects.create(
        seller=seller,
        vertical=homes,
        category=home_category,
        state=state,
        county=county,
        city="Amarillo",
        title="Browser home",
        description="Description",
        price_minor=25000000,
        currency="USD",
    )
    HomeDetails.objects.create(
        listing=home,
        property_type="house",
        beds=3,
        baths="2.0",
        square_feet=1800,
        general_area="North Amarillo",
    )
    services = Vertical.objects.create(name="Services", slug="services")
    service_category = Category.objects.create(vertical=services, name="Cleaning", slug="cleaning")
    profile = CatalogPostingProfile.objects.create(category=service_category)
    CatalogPostingField.objects.create(
        profile=profile,
        key="availability",
        label="Availability",
        field_type="choice",
        required=True,
        choices=["weekdays"],
    )
    generic = Listing.objects.create(
        seller=seller,
        vertical=services,
        category=service_category,
        state=state,
        county=county,
        city="Amarillo",
        title="Browser service",
        description="Description",
    )
    GenericListingDetails.objects.create(
        listing=generic,
        price_mode="contact",
        postal_code="79101",
        attributes={"availability": "weekdays"},
    )

    page.goto(f"{live_server.url}/login/")
    page.get_by_label("Email").fill(user.email)
    page.get_by_label("Password").fill("test-password")
    page.get_by_role("button", name="Sign in").click()
    page.goto(f"{live_server.url}/dashboard/listings/{home.id}/edit/")
    expect(page.get_by_label("Property type")).to_have_value("house")
    page.get_by_label("Title").fill("Edited browser home")
    page.get_by_role("button", name="Save listing changes").click()
    expect(page.get_by_role("heading", name="Edited browser home")).to_be_visible()
    assert page.locator("body").evaluate("(element) => element.scrollWidth <= window.innerWidth")

    page.goto(f"{live_server.url}/dashboard/listings/{generic.id}/edit/")
    expect(page.get_by_label("Availability")).to_have_value("weekdays")
    page.get_by_label("Title").fill("Edited browser service")
    page.get_by_role("button", name="Save listing changes").click()
    expect(page.get_by_role("heading", name="Edited browser service")).to_be_visible()
    assert page.locator("body").evaluate("(element) => element.scrollWidth <= window.innerWidth")
