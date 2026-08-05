from __future__ import annotations

from typing import Protocol

import pytest
from django.contrib.auth.models import Permission
from django.utils import timezone
from playwright.sync_api import Page, expect

from apps.accounts.models import SellerProfile, User
from apps.catalog.models import Category, Vertical
from apps.listings.models import Listing, ListingStatus
from apps.listings.services import create_auto_draft
from apps.locations.models import County, State

pytestmark = pytest.mark.e2e


class LiveServer(Protocol):
    url: str


@pytest.mark.django_db(transaction=True)
def test_staff_can_sign_in_to_management_console(page: Page, live_server: LiveServer) -> None:
    staff = User.objects.create_user(
        email="staff@example.com",
        password="test-password",
        is_staff=True,
    )
    staff.user_permissions.add(
        Permission.objects.get(content_type__app_label="listings", codename="moderate_listing")
    )

    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{live_server.url}/manage/login/")
    page.get_by_label("Email").fill("staff@example.com")
    page.get_by_label("Password").fill("test-password")
    page.get_by_role("button", name="Sign in to manage").click()

    expect(page).to_have_url(f"{live_server.url}/manage/")
    expect(page.get_by_role("heading", name="Marketplace operations")).to_be_visible()
    expect(page.get_by_text("Lifecycle totals", exact=True)).to_be_visible()
    expect(page.get_by_role("link", name="Moderation queue")).to_be_visible()
    assert page.locator("body").evaluate("(element) => element.scrollWidth <= window.innerWidth")


@pytest.mark.django_db(transaction=True)
def test_public_listing_report_reaches_authorized_staff_triage_queue(
    page: Page, live_server: LiveServer
) -> None:
    seller_user = User.objects.create_user(email="seller@example.test", password="test-password")
    seller = SellerProfile.objects.create(user=seller_user, display_name="Seller")
    autos = Vertical.objects.create(name="Autos", slug="autos")
    category = Category.objects.create(vertical=autos, name="Cars", slug="cars")
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
    listing = Listing.objects.create(
        seller=seller,
        vertical=autos,
        category=category,
        state=state,
        county=county,
        city="Amarillo",
        title="Reportable public listing",
        description="A public listing for report workflow coverage.",
        price_minor=100,
        currency="USD",
        status=ListingStatus.PUBLISHED,
        published_at=timezone.now(),
    )
    triager = User.objects.create_user(
        email="triager@example.test", password="test-password", is_staff=True
    )
    triager.user_permissions.add(
        Permission.objects.get(content_type__app_label="reports", codename="triage_listingreport")
    )

    page.goto(f"{live_server.url}/report-listing/{listing.id}/")
    page.get_by_label("Reason (required)").select_option("scam")
    page.get_by_label("Description").fill("Please review this listing.")
    page.get_by_role("button", name="Submit report").click()
    expect(page.get_by_role("heading", name="Thank you")).to_be_visible()

    page.context.clear_cookies()
    page.goto(f"{live_server.url}/login/")
    page.get_by_label("Email").fill("triager@example.test")
    page.get_by_label("Password").fill("test-password")
    page.get_by_role("button", name="Sign in").click()
    page.goto(f"{live_server.url}/staff/reports/")
    expect(page.get_by_role("heading", name="Listing reports")).to_be_visible()
    expect(page.get_by_text("Reportable public listing", exact=True)).to_be_visible()
    page.locator("select").select_option("acknowledge")
    page.get_by_role("button", name="Record action").click()
    expect(page.get_by_text("Report action recorded.", exact=True)).to_be_visible()


@pytest.mark.django_db(transaction=True)
def test_seller_submission_reviewer_approval_makes_listing_public(
    page: Page, live_server: LiveServer
) -> None:
    seller_user = User.objects.create_user(email="seller@example.test", password="test-password")
    seller = SellerProfile.objects.create(user=seller_user, display_name="Seller")
    autos = Vertical.objects.create(name="Autos", slug="autos")
    category = Category.objects.create(vertical=autos, name="Cars", slug="cars")
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
            "title": "Reviewable Mustang",
            "description": "Safe local car",
            "price_minor": 3000000,
            "currency": "USD",
        },
        auto_values={
            "vehicle_type": "car",
            "year": 2020,
            "make": "Ford",
            "model": "Mustang",
            "trim": "",
            "mileage": 12000,
            "title_status": "clean",
            "vin": "1HGCM82633A004352",
        },
    )
    moderator = User.objects.create_user(
        email="moderator@example.test", password="test-password", is_staff=True
    )
    moderator.user_permissions.add(
        Permission.objects.get(content_type__app_label="listings", codename="moderate_listing")
    )

    page.goto(f"{live_server.url}/login/")
    page.get_by_label("Email").fill("seller@example.test")
    page.get_by_label("Password").fill("test-password")
    page.get_by_role("button", name="Sign in").click()
    page.goto(f"{live_server.url}/dashboard/drafts/{listing.id}/")
    page.get_by_role("button", name="Submit for moderation").click()

    page.context.clear_cookies()
    page.goto(f"{live_server.url}/login/")
    page.get_by_label("Email").fill("moderator@example.test")
    page.get_by_label("Password").fill("test-password")
    page.get_by_role("button", name="Sign in").click()
    page.goto(f"{live_server.url}/staff/moderation/")
    page.get_by_role("button", name="Approve Without Payment Link").click()

    page.goto(f"{live_server.url}/texas/")
    expect(page.get_by_text("Reviewable Mustang", exact=True)).to_be_visible()
