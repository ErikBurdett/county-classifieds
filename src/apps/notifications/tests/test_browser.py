from __future__ import annotations

from typing import Protocol

import pytest
from playwright.sync_api import Page, expect

from apps.accounts.models import User
from apps.notifications.services import create_notification

pytestmark = pytest.mark.e2e


class LiveServer(Protocol):
    url: str


@pytest.mark.django_db(transaction=True)
def test_mobile_notification_bell_opens_recipient_feed(page: Page, live_server: LiveServer) -> None:
    user = User.objects.create_user(email="alerts@example.test", password="test-password")
    create_notification(
        recipient=user,
        event_type="listing.approved",
        title="Listing approved",
        body="Your listing is ready.",
        idempotency_key="browser-notification",
        destination_route="listings:dashboard",
    )
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{live_server.url}/login/")
    page.get_by_label("Email").fill(user.email)
    page.get_by_label("Password").fill("test-password")
    page.get_by_role("button", name="Sign in").click()

    bell = page.locator(".notification-center summary")
    expect(bell).to_be_visible()
    expect(bell).to_have_attribute("aria-label", "Notifications, 1 unread")
    expect(bell).not_to_contain_text("Alerts")
    bell_box = bell.bounding_box()
    assert bell_box is not None
    assert bell_box["x"] + bell_box["width"] >= 370
    bell.click()
    panel = page.locator(".notification-center__panel")
    expect(panel).to_be_visible()
    expect(panel).to_contain_text("Your listing is ready.")
    assert panel.evaluate("(element) => getComputedStyle(element).position") == "fixed"
    assert (
        panel.evaluate("(element) => getComputedStyle(element).backgroundColor")
        == "rgb(255, 255, 255)"
    )
    assert page.locator("#primary-navigation .notification-center__panel").count() == 0
    page.get_by_role("link", name="View all notifications").click()
    expect(page.get_by_role("heading", name="Notifications")).to_be_visible()
    expect(page.get_by_role("heading", name="Listing approved")).to_be_visible()
