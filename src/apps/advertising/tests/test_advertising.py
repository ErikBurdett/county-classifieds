from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from apps.advertising.catalog import PARTNER_DIRECTORY_PATH
from apps.advertising.selectors import ads_for_slot, partner_directory, sponsor_for_scope

pytestmark = pytest.mark.django_db


def test_slots_use_deterministic_static_creatives() -> None:
    inline = ads_for_slot(slot="inline", limit=4)
    banners = ads_for_slot(slot="banner")

    assert inline[0].id == "guerrilla-gear-inline"
    assert len(inline) == 4
    assert len(banners) == 4


def test_partner_directory_deduplicates_and_splits_by_link_destination() -> None:
    nationwide, founding = partner_directory()

    assert len({partner.name for partner in nationwide + founding}) == len(nationwide) + len(
        founding
    )
    assert all(partner.href != PARTNER_DIRECTORY_PATH for partner in nationwide)
    assert all(partner.href == PARTNER_DIRECTORY_PATH for partner in founding)


def test_scope_sponsors_are_deterministic_without_tracking() -> None:
    assert sponsor_for_scope(scope="48375") == sponsor_for_scope(scope="48375")
    assert sponsor_for_scope(scope="48375").slot == "inline"


def test_partner_page_renders_disclosed_safe_external_links(client: Client) -> None:
    response = client.get(reverse("advertising:partners"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Marketplace partners" in content
    assert "County founding partners" in content
    assert 'rel="noopener noreferrer sponsored"' in content
    assert 'target="_blank"' in content
    assert 'src="/static/ad-assets/LEMC250.jpg"' in content


def test_home_and_footer_slots_render_static_creatives(client: Client) -> None:
    response = client.get(reverse("core:home"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Presented by our advertisers" in content
    assert "Sponsored" in content
    assert reverse("advertising:partners") in content
