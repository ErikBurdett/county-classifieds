from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import SellerProfile, User
from apps.catalog.models import Category, Vertical
from apps.listings.models import (
    GenericListingDetails,
    Listing,
    ListingIntent,
    ListingStatus,
    ModerationActionType,
)
from apps.listings.services import moderate_listing, submit_listing
from apps.locations.models import County, State, ZipCountyReference


@pytest.fixture
def wanted_reference() -> tuple[SellerProfile, State, County, Category]:
    user = User.objects.create_user(email="wanted@example.test", password="password")
    seller = SellerProfile.objects.create(user=user, display_name="Synthetic wanted seller")
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
    ZipCountyReference.objects.create(
        postal_code="79101",
        county=county,
        source_name="test",
        source_url="https://example.test",
        release_version="test",
        release_date="2026-07-31",
        sha256_checksum="0" * 64,
        transformation_version="test",
    )
    vertical = Vertical.objects.create(name="Autos", slug="autos")
    category = Category.objects.create(vertical=vertical, name="Cars", slug="cars")
    return seller, state, county, category


@pytest.mark.django_db
def test_wanted_create_is_generic_and_optional_budget(
    client: Client, wanted_reference: tuple[SellerProfile, State, County, Category]
) -> None:
    seller, state, county, category = wanted_reference
    client.force_login(seller.user)

    advance = client.post(
        reverse("listings:create_wanted_listing"),
        {"show_fields": "1", "vertical": category.vertical_id, "category": category.id},
    )
    assert advance.status_code == 200
    assert b"Vehicle type" not in advance.content
    assert b"Budget preference" in advance.content
    assert b"Correct the errors below." not in advance.content

    response = client.post(
        reverse("listings:create_wanted_listing"),
        {
            "vertical": category.vertical_id,
            "category": category.id,
            "state": state.id,
            "county": county.id,
            "city": "Amarillo",
            "title": "Synthetic wanted car",
            "description": "Synthetic local request only.",
            "price_mode": "contact",
            "postal_code": "79101",
        },
    )
    assert response.status_code == 302
    listing = Listing.objects.get(title="Synthetic wanted car")
    assert listing.intent == ListingIntent.WANTED
    assert listing.listing_kind_id is None
    assert GenericListingDetails.objects.get(listing=listing).price_mode == "contact"
    assert not hasattr(listing, "auto_details")


@pytest.mark.django_db
def test_wanted_public_browse_is_explicit_and_uses_moderation(
    client: Client, wanted_reference: tuple[SellerProfile, State, County, Category]
) -> None:
    seller, state, county, category = wanted_reference
    listing = Listing.objects.create(
        seller=seller,
        intent=ListingIntent.WANTED,
        vertical=category.vertical,
        category=category,
        state=state,
        county=county,
        city="Amarillo",
        title="Wanted tractor",
        description="Synthetic",
    )
    GenericListingDetails.objects.create(listing=listing, price_mode="contact", postal_code="79101")
    submit_listing(listing_id=listing.id, seller=seller)
    listing.refresh_from_db()
    moderator = User.objects.create_superuser(
        email="wanted-moderator@example.test", password="password"
    )
    moderate_listing(
        listing_id=listing.id,
        actor=moderator,
        revision=listing.lifecycle_revision,
        outcome=ModerationActionType.APPROVED,
    )
    listing.refresh_from_db()
    assert listing.status == ListingStatus.PUBLISHED
    assert listing.expires_at is None
    assert b"Wanted tractor" not in client.get(f"/{state.slug}/").content
    wanted = client.get(reverse("locations:in_search_of"), {"state": state.id})
    assert wanted.status_code == 200
    assert b"Wanted tractor" in wanted.content
    assert b"Wanted" in wanted.content
