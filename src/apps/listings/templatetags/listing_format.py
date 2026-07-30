from __future__ import annotations

from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def listing_price(price_minor: int | None, currency: str) -> str:
    """Format stored integer minor units without exposing implementation detail."""

    if price_minor is None:
        return "Contact for price"
    amount = Decimal(price_minor) / Decimal(100)
    if currency == "USD":
        return f"${amount:,.2f}"
    return f"{currency} {amount:,.2f}"
