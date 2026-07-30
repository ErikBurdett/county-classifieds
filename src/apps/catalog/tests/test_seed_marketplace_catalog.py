from __future__ import annotations

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import models
from django.test import override_settings

from apps.catalog.management.commands.seed_marketplace_catalog import profile_fields_for
from apps.catalog.marketplace_catalog import MARKETPLACE_CATALOG
from apps.catalog.models import (
    CatalogPostingField,
    CatalogPostingProfile,
    Category,
    ListingKind,
    ListingProduct,
    Vertical,
)
from apps.listings.workflows import resolve_listing_workflow

pytestmark = pytest.mark.django_db


def catalog_category_count() -> int:
    return sum(len(vertical.categories) for vertical in MARKETPLACE_CATALOG)


@override_settings(DEBUG=True)
def test_marketplace_catalog_seed_is_idempotent_and_complete() -> None:
    call_command("seed_marketplace_catalog")
    call_command("seed_marketplace_catalog")

    assert set(Vertical.objects.values_list("slug", flat=True)) == {
        vertical.slug for vertical in MARKETPLACE_CATALOG
    }
    assert Category.objects.count() == catalog_category_count()
    assert Category.objects.filter(is_active=True).count() == catalog_category_count()
    assert Category.objects.filter(parent__isnull=False, parent__parent__isnull=False).count() == 0
    assert (
        not Category.objects.exclude(parent__isnull=True)
        .exclude(vertical_id=models.F("parent__vertical_id"))
        .exists()
    )
    leaves = Category.objects.filter(is_active=True, vertical__is_active=True).exclude(
        children__is_active=True
    )
    generic_leaves = [
        category
        for category in leaves.select_related("vertical", "parent")
        if not resolve_listing_workflow(category=category).typed
    ]
    assert len(generic_leaves) == 103
    assert CatalogPostingProfile.objects.filter(is_active=True).count() == len(generic_leaves)
    assert CatalogPostingField.objects.filter(profile__is_active=True).count() == 671
    for vertical in Vertical.objects.order_by("slug"):
        leaf = next(category for category in leaves if category.vertical_id == vertical.id)
        workflow = resolve_listing_workflow(category=leaf)
        profile = CatalogPostingProfile.objects.filter(category=leaf, is_active=True).first()
        if workflow.typed:
            assert profile is None
        else:
            assert profile is not None
            assert profile.version == 2
            assert profile.fields.count() == len(profile_fields_for(category=leaf))


@override_settings(DEBUG=True)
def test_marketplace_catalog_seed_preserves_unknown_profile_fields() -> None:
    call_command("seed_marketplace_catalog")
    category = Category.objects.get(vertical__slug="services", slug="cleaning")
    profile = CatalogPostingProfile.objects.get(category=category)
    CatalogPostingField.objects.create(
        profile=profile,
        key="historical_note",
        label="Historical note",
        field_type="text",
        maximum=120,
    )

    call_command("seed_marketplace_catalog")

    profile.refresh_from_db()
    assert profile.version == 2
    assert profile.is_active
    assert profile.fields.filter(key="historical_note").exists()


@override_settings(DEBUG=True)
def test_marketplace_catalog_seed_keeps_autos_urls_active_and_creates_no_products() -> None:
    autos = Vertical.objects.create(name="Autos", slug="autos", is_active=False)
    for name, slug in (
        ("Cars", "cars"),
        ("Trucks", "trucks"),
        ("SUVs", "suvs"),
        ("Vans", "vans"),
        ("Motorcycles", "motorcycles"),
        ("Other Autos", "other-autos"),
    ):
        Category.objects.create(vertical=autos, name=name, slug=slug, is_active=False)

    call_command("seed_marketplace_catalog")

    autos.refresh_from_db()
    assert autos.is_active
    assert set(
        Category.objects.filter(vertical=autos, is_active=True).values_list("slug", flat=True)
    ) >= {"cars", "trucks", "suvs", "vans", "motorcycles", "other-autos"}
    assert not ListingKind.objects.exclude(vertical=autos).exists()
    assert not ListingProduct.objects.exclude(listing_kind__vertical=autos).exists()
    assert not ListingKind.objects.exists()
    assert not ListingProduct.objects.exists()


@override_settings(DEBUG=True)
def test_marketplace_catalog_seeds_others_with_a_single_general_leaf() -> None:
    call_command("seed_marketplace_catalog")
    call_command("seed_marketplace_catalog")

    others = Vertical.objects.get(slug="others")
    assert others.is_active
    assert list(
        Category.objects.filter(vertical=others, is_active=True).values_list("slug", flat=True)
    ) == ["general"]
    profile = CatalogPostingProfile.objects.get(category__vertical=others, category__slug="general")
    assert profile.is_active
    assert list(profile.fields.values_list("key", flat=True)) == [
        "condition",
        "quantity",
        "fulfillment",
    ]


@override_settings(DEBUG=True)
def test_marketplace_catalog_seed_preserves_unowned_staff_records() -> None:
    staff_vertical = Vertical.objects.create(
        name="Staff vertical", slug="staff-vertical", display_order=999, is_active=False
    )
    staff_category = Category.objects.create(
        vertical=staff_vertical,
        name="Staff category",
        slug="staff-category",
        display_order=999,
        is_active=False,
    )

    call_command("seed_marketplace_catalog")

    staff_vertical.refresh_from_db()
    staff_category.refresh_from_db()
    assert (staff_vertical.name, staff_vertical.display_order, staff_vertical.is_active) == (
        "Staff vertical",
        999,
        False,
    )
    assert (staff_category.name, staff_category.display_order, staff_category.is_active) == (
        "Staff category",
        999,
        False,
    )


@override_settings(DEBUG=True)
def test_marketplace_catalog_excludes_prohibited_catalog_groups() -> None:
    call_command("seed_marketplace_catalog")

    prohibited_terms = (
        "firearm",
        "weapon",
        "controlled substance",
        "adult service",
        "financial",
        "crypto",
    )
    catalog_names = Category.objects.values_list("name", flat=True)
    assert all(term not in name.lower() for name in catalog_names for term in prohibited_terms)


@override_settings(DEBUG=False)
def test_marketplace_catalog_seed_refuses_non_debug() -> None:
    with pytest.raises(CommandError, match="DEBUG"):
        call_command("seed_marketplace_catalog")
