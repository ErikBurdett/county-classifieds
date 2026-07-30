from __future__ import annotations

from collections.abc import Callable

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import DatabaseError, connection, transaction
from django.test import Client, override_settings
from django.urls import reverse

from apps.accounts.models import SellerProfile, User
from apps.catalog.models import Category, Vertical
from apps.listings.models import HomeGoodsDetails, Listing, ListingStatus
from apps.listings.services import (
    create_appliances_draft,
    create_home_garden_draft,
    update_appliances_draft,
    update_home_garden_draft,
)
from apps.locations.models import County, State

pytestmark = pytest.mark.django_db

DraftCreateService = Callable[..., Listing]
DraftUpdateService = Callable[..., Listing]


@pytest.fixture
def home_goods_references() -> tuple[Category, Category, State, County]:
    appliances = Vertical.objects.create(name="Appliances", slug="appliances")
    home_garden = Vertical.objects.create(name="Home & Garden", slug="home-garden")
    appliances_category = Category.objects.create(
        vertical=appliances, name="Kitchen Appliances", slug="kitchen-appliances"
    )
    home_garden_category = Category.objects.create(
        vertical=home_garden, name="Furniture", slug="furniture"
    )
    state = State.objects.create(
        fips="48", usps_code="TX", name="Texas", slug="texas", is_active=True
    )
    county = County.objects.create(
        fips="48375", state=state, name="Potter", slug="potter", is_active=True
    )
    return appliances_category, home_garden_category, state, county


@pytest.fixture
def seller() -> SellerProfile:
    user = User.objects.create_user(email="home-goods@example.com", password="test-password")
    return SellerProfile.objects.create(user=user, display_name="Home goods seller")


def listing_values(
    category: Category, state: State, county: County, title: str
) -> dict[str, object]:
    return {
        "category": category,
        "state": state,
        "county": county,
        "city": "Amarillo",
        "title": title,
        "description": "Private Home Goods draft",
        "price_minor": 10000,
        "currency": "USD",
    }


def home_goods_values() -> dict[str, object]:
    return {
        "item_type": "Refrigerator",
        "brand": "Example",
        "condition": "good",
        "working_status": "working",
        "dimensions": "30 in W x 32 in D x 66 in H",
        "fulfillment_preference": "pickup",
    }


@pytest.mark.parametrize(
    ("create_service", "category_index", "expected_vertical"),
    [
        (create_appliances_draft, 0, "appliances"),
        (create_home_garden_draft, 1, "home-garden"),
    ],
)
def test_create_home_goods_drafts_use_fixed_supported_verticals(
    seller: SellerProfile,
    home_goods_references: tuple[Category, Category, State, County],
    create_service: DraftCreateService,
    category_index: int,
    expected_vertical: str,
) -> None:
    appliances_category, home_garden_category, state, county = home_goods_references
    category = (appliances_category, home_garden_category)[category_index]

    listing = create_service(
        seller=seller,
        listing_values=listing_values(category, state, county, "Private draft"),
        home_goods_values=home_goods_values(),
    )

    assert listing.status == ListingStatus.DRAFT
    assert listing.vertical.slug == expected_vertical
    assert listing.home_goods_details.item_type == "Refrigerator"


def test_home_goods_details_validate_nonblank_item_type() -> None:
    details = HomeGoodsDetails(**{**home_goods_values(), "item_type": "   "})

    with pytest.raises(ValidationError) as error:
        details.full_clean()

    assert "item_type" in error.value.message_dict


@pytest.mark.parametrize(
    ("create_service", "update_service", "category_index"),
    [
        (create_appliances_draft, update_appliances_draft, 0),
        (create_home_garden_draft, update_home_garden_draft, 1),
    ],
)
def test_home_goods_updates_require_owner_and_depublish_published_listing(
    seller: SellerProfile,
    home_goods_references: tuple[Category, Category, State, County],
    create_service: DraftCreateService,
    update_service: DraftUpdateService,
    category_index: int,
) -> None:
    appliances_category, home_garden_category, state, county = home_goods_references
    category = (appliances_category, home_garden_category)[category_index]
    listing = create_service(
        seller=seller,
        listing_values=listing_values(category, state, county, "Private draft"),
        home_goods_values=home_goods_values(),
    )
    other = SellerProfile.objects.create(
        user=User.objects.create_user(email="other@example.com", password="test-password"),
        display_name="Other seller",
    )

    with pytest.raises(PermissionDenied):
        update_service(
            listing_id=listing.id,
            seller=other,
            listing_values=listing_values(category, state, county, "Changed draft"),
            home_goods_values=home_goods_values(),
        )

    listing.status = ListingStatus.PUBLISHED
    listing.published_at = listing.created_at
    listing.save(update_fields=("status", "published_at"))
    updated = update_service(
        listing_id=listing.id,
        seller=seller,
        listing_values=listing_values(category, state, county, "Changed draft"),
        home_goods_values=home_goods_values(),
    )
    assert updated.status == ListingStatus.IN_REVIEW
    assert updated.published_at is None


@pytest.mark.parametrize(
    "case",
    [
        (
            "create_appliances_draft",
            "appliances_draft_detail",
            "edit_appliances_draft",
            0,
        ),
        (
            "create_home_garden_draft",
            "home_garden_draft_detail",
            "edit_home_garden_draft",
            1,
        ),
    ],
)
def test_home_goods_routes_are_private_and_ignore_status_vertical_tampering(
    client: Client,
    seller: SellerProfile,
    home_goods_references: tuple[Category, Category, State, County],
    case: tuple[str, str, str, int],
) -> None:
    appliances_category, home_garden_category, state, county = home_goods_references
    create_name, detail_name, edit_name, category_index = case
    category = (appliances_category, home_garden_category)[category_index]
    assert client.get(reverse(f"listings:{create_name}")).status_code == 302

    client.force_login(seller.user)
    title = f"{create_name} title"
    response = client.post(
        reverse(f"listings:{create_name}"),
        {
            **listing_values(category, state, county, title),
            **home_goods_values(),
            "category": category.id,
            "state": state.id,
            "county": county.id,
            "vertical": "autos",
            "status": ListingStatus.PUBLISHED,
        },
    )
    assert response.status_code == 302
    listing = Listing.objects.get(seller=seller, title=title)
    assert listing.status == ListingStatus.DRAFT
    assert listing.vertical_id == category.vertical_id
    assert (
        client.get(
            reverse(f"listings:{detail_name}", kwargs={"listing_id": listing.id})
        ).status_code
        == 200
    )

    edit_url = reverse(f"listings:{edit_name}", kwargs={"listing_id": listing.id})
    response = client.post(
        edit_url,
        {
            **listing_values(category, state, county, f"{title} updated"),
            **home_goods_values(),
            "category": category.id,
            "state": state.id,
            "county": county.id,
            "vertical": "autos",
            "status": ListingStatus.PUBLISHED,
        },
    )
    assert response.status_code == 302
    listing.refresh_from_db()
    assert listing.status == ListingStatus.DRAFT
    assert listing.title == f"{title} updated"

    other = User.objects.create_user(email="route-other@example.com", password="test-password")
    SellerProfile.objects.create(user=other, display_name="Route other")
    client.force_login(other)
    assert (
        client.get(
            reverse(f"listings:{detail_name}", kwargs={"listing_id": listing.id})
        ).status_code
        == 404
    )


@pytest.mark.skipif(connection.vendor != "postgresql", reason="PostgreSQL trigger coverage")
def test_postgresql_rejects_incompatible_home_goods_detail_and_vertical_change(
    seller: SellerProfile, home_goods_references: tuple[Category, Category, State, County]
) -> None:
    appliances_category, home_garden_category, state, county = home_goods_references
    listing = create_appliances_draft(
        seller=seller,
        listing_values=listing_values(appliances_category, state, county, "Refrigerator"),
        home_goods_values=home_goods_values(),
    )
    autos = Vertical.objects.create(name="Autos", slug="autos")
    autos_category = Category.objects.create(vertical=autos, name="Cars", slug="cars")
    with pytest.raises(DatabaseError), transaction.atomic():
        listing.vertical = autos
        listing.category = autos_category
        listing.save(update_fields=("vertical", "category"))

    invalid_listing = Listing.objects.create(
        seller=seller,
        vertical=autos,
        category=autos_category,
        state=state,
        county=county,
        city="Amarillo",
        title="Wrong Home Goods details",
        description="Wrong Home Goods details",
        price_minor=100,
        currency="USD",
    )
    with pytest.raises(DatabaseError), transaction.atomic():
        HomeGoodsDetails.objects.create(listing=invalid_listing, **home_goods_values())

    assert home_garden_category.vertical.slug == "home-garden"


@override_settings(DEBUG=True)
def test_home_goods_seed_is_idempotent(
    home_goods_references: tuple[Category, Category, State, County],
) -> None:
    for email in ("telephoneheater@local.test", "albuquerque@local.test"):
        user = User.objects.create_user(email=email, password="test-password")
        SellerProfile.objects.create(user=user, display_name=email)

    call_command("seed_demo_home_goods_drafts")
    call_command("seed_demo_home_goods_drafts")

    assert Listing.objects.filter(title__startswith="Demo private").count() == 2
    assert Listing.objects.filter(status=ListingStatus.PUBLISHED).count() == 0
