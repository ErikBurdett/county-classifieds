"""Server-owned category-to-listing-workflow resolution."""

from __future__ import annotations

from dataclasses import dataclass

from apps.catalog.models import Category

from .models import ListingIntent


@dataclass(frozen=True)
class ListingWorkflow:
    key: str
    typed: bool


GENERIC = ListingWorkflow(key="generic", typed=False)
TYPED_WORKFLOWS = {
    "autos": ListingWorkflow(key="auto", typed=True),
    "real-estate": ListingWorkflow(key="home", typed=True),
    "rentals": ListingWorkflow(key="rental", typed=True),
    "livestock-animals": ListingWorkflow(key="livestock", typed=True),
    "home-garden": ListingWorkflow(key="home_goods", typed=True),
    "appliances": ListingWorkflow(key="home_goods", typed=True),
}


def is_postable_leaf(*, category: Category) -> bool:
    return (
        category.is_active
        and category.vertical.is_active
        and not category.children.filter(is_active=True).exists()
    )


def resolve_listing_workflow(
    *, category: Category, intent: str = ListingIntent.OFFER
) -> ListingWorkflow:
    """Resolve by actual leaf category, including Farm & Ranch subtypes."""
    if not is_postable_leaf(category=category):
        raise ValueError("Choose a postable subcategory.")
    if intent == ListingIntent.WANTED:
        return GENERIC
    if category.vertical.slug == "farm-ranch":
        if category.slug == "pasture-lease":
            return ListingWorkflow(key="pasture", typed=True)
        if category.slug in {"tractors", "harvesting-equipment", "implements"}:
            return ListingWorkflow(key="ag_equipment", typed=True)
        return GENERIC
    if category.vertical.slug == "livestock-animals" and category.slug in {
        "cattle",
        "goats-sheep",
        "horses",
        "poultry",
    }:
        return TYPED_WORKFLOWS["livestock-animals"]
    return TYPED_WORKFLOWS.get(category.vertical.slug, GENERIC)
