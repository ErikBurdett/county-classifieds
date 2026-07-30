from __future__ import annotations

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client
from django.test.utils import override_settings

from apps.listings.models import (
    GenericListingDetails,
    Listing,
    ListingCategoryTag,
    ListingCustomField,
    ListingSellerTag,
    ListingStatus,
)
from apps.listings.selectors import public_listings
from apps.locations.forms import PublicBrowseForm, apply_public_filters
from apps.locations.models import County, State

pytestmark = pytest.mark.django_db


@pytest.fixture
def generic_demo_county() -> County:
    state = State.objects.create(
        fips="48",
        usps_code="TX",
        name="Texas",
        slug="texas",
        is_active=True,
        is_network_enabled=True,
    )
    return County.objects.create(
        fips="48375",
        state=state,
        name="Potter",
        slug="potter",
        is_active=True,
        is_network_enabled=True,
    )


@override_settings(DEBUG=True)
def test_generic_taxonomy_demo_seed_is_idempotent_and_public(
    generic_demo_county: County, capsys: pytest.CaptureFixture[str]
) -> None:
    call_command("seed_marketplace_catalog")
    call_command("seed_demo_generic_taxonomy")
    first_run = capsys.readouterr().out
    call_command("seed_demo_generic_taxonomy")
    second_run = capsys.readouterr().out

    listings = list(
        Listing.objects.filter(
            county=generic_demo_county,
            title__startswith="Synthetic taxonomy fixture:",
        )
        .select_related("category", "vertical")
        .prefetch_related("controlled_tags__category", "seller_tags", "custom_fields")
        .order_by("title")
    )

    assert len(listings) == 6
    assert {listing.vertical.slug for listing in listings} == {
        "services",
        "business-industrial",
        "jobs",
        "collectibles-art",
        "electronics",
        "others",
    }
    assert all(listing.status == ListingStatus.PUBLISHED for listing in listings)
    assert all(
        GenericListingDetails.objects.filter(listing=listing).exists() for listing in listings
    )
    assert all(not hasattr(listing, "home_goods_details") for listing in listings)
    assert all(
        ListingCategoryTag.objects.filter(listing=listing).count() == 2
        for listing in listings
        if listing.vertical.slug != "others"
    )
    others = next(listing for listing in listings if listing.vertical.slug == "others")
    assert list(
        ListingCategoryTag.objects.filter(listing=others).values_list("category__slug", flat=True)
    ) == ["general"]
    assert all(
        ListingSellerTag.objects.filter(listing=listing).count() == 1 for listing in listings
    )
    assert all(
        ListingCustomField.objects.filter(listing=listing).count() == 1 for listing in listings
    )
    assert "6 created" in first_run
    assert "6 unchanged" in second_run


@override_settings(DEBUG=False)
def test_generic_taxonomy_demo_seed_refuses_non_debug() -> None:
    with pytest.raises(CommandError, match="DEBUG"):
        call_command("seed_demo_generic_taxonomy")


@override_settings(DEBUG=True)
def test_generic_taxonomy_seeded_tag_is_public_searchable_but_fact_is_not(
    client: Client, generic_demo_county: County
) -> None:
    call_command("seed_marketplace_catalog")
    call_command("seed_demo_generic_taxonomy")
    listing = Listing.objects.get(title__startswith="Synthetic taxonomy fixture: services")
    tag = listing.seller_tags.get().value
    fact = listing.custom_fields.get().value

    tag_form = PublicBrowseForm({"q": tag}, state=generic_demo_county.state)
    fact_form = PublicBrowseForm({"q": fact}, state=generic_demo_county.state)
    assert tag_form.is_valid() and fact_form.is_valid()
    assert list(apply_public_filters(public_listings(), tag_form)) == [listing]
    assert not apply_public_filters(public_listings(), fact_form).exists()

    response = client.get(f"/texas/potter/listing/{listing.id}/")
    assert response.status_code == 200
    assert b"Tags" in response.content
    assert tag.encode() in response.content
    assert b"Additional details" in response.content
    assert fact.encode() in response.content


@override_settings(DEBUG=True)
def test_others_demo_tag_is_public_after_approval(
    client: Client, generic_demo_county: County
) -> None:
    call_command("seed_marketplace_catalog")
    call_command("seed_demo_generic_taxonomy")
    listing = Listing.objects.get(title__startswith="Synthetic taxonomy fixture: others")
    tag = listing.seller_tags.get().value

    form = PublicBrowseForm({"q": tag}, state=generic_demo_county.state)
    assert form.is_valid()
    assert list(apply_public_filters(public_listings(), form)) == [listing]

    response = client.get(f"/texas/potter/listing/{listing.id}/")
    assert response.status_code == 200
    assert b"Others" in response.content
    assert b"General" not in response.content
    assert tag.encode() in response.content
