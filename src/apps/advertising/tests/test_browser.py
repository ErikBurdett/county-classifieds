from __future__ import annotations

from typing import Protocol

import pytest
from django.core.management import call_command
from django.test import override_settings
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


class LiveServer(Protocol):
    url: str


def test_sponsored_slots_and_partner_directory_are_mobile_usable(
    page: Page, live_server: LiveServer
) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(live_server.url)

    slot = page.get_by_label("Sponsored advertisements").first
    expect(slot).to_be_visible()
    expect(slot.get_by_role("button", name="Next advertisement")).to_be_visible()
    sponsored_link = slot.locator('a[rel="noopener noreferrer sponsored"]').first
    expect(sponsored_link).to_have_attribute("target", "_blank")
    expect(sponsored_link.locator("img")).to_have_attribute(
        "src", "/static/ad-assets/ad-guerilla-gear.png"
    )

    page.get_by_role("link", name="Partners").click()
    expect(page.get_by_role("heading", name="Marketplace partners")).to_be_visible()
    expect(page.get_by_role("heading", name="Nationwide partners")).to_be_visible()
    expect(page.get_by_role("heading", name="County founding partners")).to_be_visible()
    assert page.locator("body").evaluate("(element) => element.scrollWidth <= window.innerWidth")


@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_county_browse_has_hero_filter_and_in_feed_sponsors(
    page: Page, live_server: LiveServer
) -> None:
    call_command("seed_demo_marketplace", verbosity=0)
    page.goto(f"{live_server.url}/texas/potter/")

    expect(page.locator(".browse-hero .compact-sponsor")).to_be_visible()
    expect(page.locator(".filter-panel .compact-sponsor")).to_be_visible()
    expect(page.locator(".listing-card-ad").first).to_be_visible()
    in_feed_ad = page.locator(".listing-card-ad__creative").first
    expect(in_feed_ad).to_have_attribute("aria-label", "Advertisement: Guerrilla Gear")
    expect(in_feed_ad.locator("img")).to_have_attribute(
        "src", "/static/ad-assets/ad-guerilla-gear.png"
    )
    assert (
        in_feed_ad.locator("img").evaluate("(image) => getComputedStyle(image).objectFit")
        == "contain"
    )
    assert in_feed_ad.evaluate(
        "(ad) => { const box = ad.getBoundingClientRect(); "
        "return Math.abs((box.width / box.height) - 1.2) < 0.02; }"
    )
