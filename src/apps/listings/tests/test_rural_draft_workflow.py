from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import DatabaseError, connection, transaction
from django.test import Client, override_settings
from django.urls import reverse

from apps.accounts.models import SellerProfile, User
from apps.catalog.models import Category, Vertical
from apps.listings.models import (
    AgEquipmentDetails,
    Listing,
    ListingStatus,
    LivestockDetails,
    PastureDetails,
)
from apps.listings.services import (
    create_ag_equipment_draft,
    create_livestock_draft,
    create_pasture_draft,
    update_ag_equipment_draft,
    update_livestock_draft,
    update_pasture_draft,
)
from apps.locations.models import County, State

pytestmark = pytest.mark.django_db

DraftUpdateService = Callable[..., Listing]
DetailValues = Callable[[], dict[str, object]]


@pytest.fixture
def rural_references() -> tuple[Category, Category, Category, State, County]:
    farm_ranch = Vertical.objects.create(name="Farm & Ranch", slug="farm-ranch")
    livestock = Vertical.objects.create(name="Livestock & Animals", slug="livestock-animals")
    ag_category = Category.objects.create(
        vertical=farm_ranch, name="Farm Equipment", slug="farm-equipment"
    )
    livestock_category = Category.objects.create(
        vertical=livestock, name="Livestock", slug="livestock"
    )
    pasture_category = Category.objects.create(
        vertical=farm_ranch, name="Land & Pasture", slug="land-pasture"
    )
    state = State.objects.create(
        fips="48", usps_code="TX", name="Texas", slug="texas", is_active=True
    )
    county = County.objects.create(
        fips="48375", state=state, name="Potter", slug="potter", is_active=True
    )
    return ag_category, livestock_category, pasture_category, state, county


@pytest.fixture
def seller() -> SellerProfile:
    user = User.objects.create_user(email="rural@example.com", password="test-password")
    return SellerProfile.objects.create(user=user, display_name="Rural seller")


def listing_values(
    category: Category, state: State, county: County, title: str
) -> dict[str, object]:
    return {
        "category": category,
        "state": state,
        "county": county,
        "city": "Amarillo",
        "title": title,
        "description": "Private rural draft",
        "price_minor": 100000,
        "currency": "USD",
    }


def ag_equipment_values() -> dict[str, object]:
    return {
        "equipment_type": "tractor",
        "make": "Field",
        "model": "50",
        "year": 2015,
        "hours": 1200,
        "powered": True,
        "condition": "used",
    }


def livestock_values() -> dict[str, object]:
    return {
        "species": "cattle",
        "breed": "Mixed",
        "animal_class": "Cow-calf pair",
        "head_count": 4,
        "age_or_weight": "Mature",
        "sale_unit": "head",
    }


def pasture_values() -> dict[str, object]:
    return {
        "acreage": Decimal("40.00"),
        "water_available": True,
        "fenced": True,
        "lease_term": "Annual lease",
        "use_restrictions": "Grazing only",
        "available_date": date(2026, 9, 1),
    }


def test_create_rural_drafts_use_fixed_catalog_verticals(
    seller: SellerProfile, rural_references: tuple[Category, Category, Category, State, County]
) -> None:
    ag_category, livestock_category, pasture_category, state, county = rural_references
    ag = create_ag_equipment_draft(
        seller=seller,
        listing_values=listing_values(ag_category, state, county, "Tractor"),
        ag_equipment_values=ag_equipment_values(),
    )
    livestock = create_livestock_draft(
        seller=seller,
        listing_values=listing_values(livestock_category, state, county, "Cattle"),
        livestock_values=livestock_values(),
    )
    pasture = create_pasture_draft(
        seller=seller,
        listing_values=listing_values(pasture_category, state, county, "Pasture"),
        pasture_values=pasture_values(),
    )

    assert ag.status == ListingStatus.DRAFT
    assert ag.vertical.slug == "farm-ranch"
    assert livestock.vertical.slug == "livestock-animals"
    assert pasture.vertical.slug == "farm-ranch"


@pytest.mark.parametrize(
    ("detail_model", "values", "field"),
    [
        (AgEquipmentDetails, {**ag_equipment_values(), "hours": -1}, "hours"),
        (LivestockDetails, {**livestock_values(), "head_count": 0}, "__all__"),
        (PastureDetails, {**pasture_values(), "acreage": Decimal("0")}, "acreage"),
    ],
)
def test_rural_detail_models_validate_safe_typed_fields(
    detail_model: type[AgEquipmentDetails] | type[LivestockDetails] | type[PastureDetails],
    values: dict[str, object],
    field: str,
) -> None:
    details = detail_model(**values)
    with pytest.raises(ValidationError) as error:
        details.full_clean()
    assert field in error.value.message_dict


@pytest.mark.parametrize(
    "case",
    [
        (
            create_ag_equipment_draft,
            update_ag_equipment_draft,
            0,
            "ag_equipment_values",
            ag_equipment_values,
        ),
        (
            create_livestock_draft,
            update_livestock_draft,
            1,
            "livestock_values",
            livestock_values,
        ),
        (create_pasture_draft, update_pasture_draft, 2, "pasture_values", pasture_values),
    ],
)
def test_rural_update_services_require_the_owner_and_draft_state(
    seller: SellerProfile,
    rural_references: tuple[Category, Category, Category, State, County],
    case: tuple[Callable[..., Listing], DraftUpdateService, int, str, DetailValues],
) -> None:
    create_service, update_service, category_index, details_key, detail_values = case
    ag_category, livestock_category, pasture_category, state, county = rural_references
    categories = (ag_category, livestock_category, pasture_category)
    category = categories[category_index]
    listing = create_service(
        seller=seller,
        listing_values=listing_values(category, state, county, "Private draft"),
        **{details_key: detail_values()},
    )
    other = SellerProfile.objects.create(
        user=User.objects.create_user(
            email=f"other-{details_key}@example.com", password="test-password"
        ),
        display_name="Other seller",
    )
    with pytest.raises(PermissionDenied):
        update_service(
            listing_id=listing.id,
            seller=other,
            listing_values=listing_values(category, state, county, "Changed draft"),
            **{details_key: detail_values()},
        )


@pytest.mark.parametrize(
    ("case", "edit_name"),
    [
        (
            ("create_ag_equipment_draft", "ag_equipment_draft_detail", 0, ag_equipment_values),
            "edit_ag_equipment_draft",
        ),
        (
            ("create_livestock_draft", "livestock_draft_detail", 1, livestock_values),
            "edit_livestock_draft",
        ),
        (
            ("create_pasture_draft", "pasture_draft_detail", 2, pasture_values),
            "edit_pasture_draft",
        ),
    ],
)
def test_rural_requests_are_private_owner_scoped_and_ignore_vertical_tampering(
    client: Client,
    seller: SellerProfile,
    rural_references: tuple[Category, Category, Category, State, County],
    case: tuple[str, str, int, DetailValues],
    edit_name: str,
) -> None:
    create_name, detail_name, category_index, detail_values = case
    ag_category, livestock_category, pasture_category, state, county = rural_references
    categories = (ag_category, livestock_category, pasture_category)
    category = categories[category_index]
    assert client.get(reverse(f"listings:{create_name}")).status_code == 302

    client.force_login(seller.user)
    assert client.get(reverse(f"listings:{create_name}")).status_code == 200
    title = f"{create_name} title"
    response = client.post(
        reverse(f"listings:{create_name}"),
        {
            **listing_values(category, state, county, title),
            **detail_values(),
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
    assert client.get(edit_url).status_code == 200
    response = client.post(
        edit_url,
        {
            **listing_values(category, state, county, f"{title} updated"),
            **detail_values(),
            "category": category.id,
            "state": state.id,
            "county": county.id,
            "vertical": "autos",
            "status": ListingStatus.PUBLISHED,
        },
    )
    assert response.status_code == 302
    listing.refresh_from_db()
    assert listing.title == f"{title} updated"
    assert listing.status == ListingStatus.DRAFT

    other = User.objects.create_user(
        email=f"{create_name}-other@example.com", password="test-password"
    )
    SellerProfile.objects.create(user=other, display_name="Other seller")
    client.force_login(other)
    assert (
        client.get(
            reverse(f"listings:{detail_name}", kwargs={"listing_id": listing.id})
        ).status_code
        == 404
    )


@pytest.mark.skipif(connection.vendor != "postgresql", reason="PostgreSQL trigger coverage")
def test_postgresql_rejects_incompatible_rural_detail_and_vertical_change(
    seller: SellerProfile, rural_references: tuple[Category, Category, Category, State, County]
) -> None:
    ag_category, livestock_category, _pasture_category, state, county = rural_references
    ag = create_ag_equipment_draft(
        seller=seller,
        listing_values=listing_values(ag_category, state, county, "Tractor"),
        ag_equipment_values=ag_equipment_values(),
    )
    with pytest.raises(DatabaseError), transaction.atomic():
        ag.vertical = livestock_category.vertical
        ag.category = livestock_category
        ag.save(update_fields=("vertical", "category"))

    invalid_listing = Listing.objects.create(
        seller=seller,
        vertical=ag_category.vertical,
        category=ag_category,
        state=state,
        county=county,
        city="Amarillo",
        title="Wrong livestock details",
        description="Wrong livestock details",
        price_minor=100,
        currency="USD",
    )
    with pytest.raises(DatabaseError), transaction.atomic():
        LivestockDetails.objects.create(listing=invalid_listing, **livestock_values())


@override_settings(DEBUG=True)
def test_rural_seed_is_idempotent(
    rural_references: tuple[Category, Category, Category, State, County],
) -> None:
    for email in ("telephoneheater@local.test", "albuquerque@local.test"):
        user = User.objects.create_user(email=email, password="test-password")
        SellerProfile.objects.create(user=user, display_name=email)

    call_command("seed_demo_rural_drafts")
    call_command("seed_demo_rural_drafts")

    assert Listing.objects.filter(title__startswith="Demo private").count() == 3
    assert Listing.objects.filter(status=ListingStatus.PUBLISHED).count() == 0
