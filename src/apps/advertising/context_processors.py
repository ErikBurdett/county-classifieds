from __future__ import annotations

from typing import Any

from .selectors import ads_for_slot, sponsor_for_scope


def advertising_slots(_request: object) -> dict[str, Any]:
    """Make the global footer banner available without database work."""
    return {
        "footer_banner_ads": ads_for_slot(slot="banner", limit=4),
        "market_finder_sponsor_ad": sponsor_for_scope(scope="market-finder"),
        "filter_sponsor_ad": sponsor_for_scope(scope="listing-filters"),
    }
