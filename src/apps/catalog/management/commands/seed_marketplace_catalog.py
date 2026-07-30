from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog.marketplace_catalog import (
    MARKETPLACE_CATALOG,
    MARKETPLACE_CATALOG_VERSION,
    CategorySeed,
    VerticalSeed,
)
from apps.catalog.models import CatalogPostingField, CatalogPostingProfile, Category, Vertical
from apps.listings.workflows import resolve_listing_workflow

PROFILE_VERSION = 2
FieldSeed = tuple[str, str, str, bool, tuple[str, ...], bool]

CONDITION: FieldSeed = (
    "condition",
    "Condition",
    "choice",
    True,
    ("new", "like_new", "good", "fair"),
    True,
)
FULFILLMENT: FieldSeed = (
    "fulfillment",
    "Pickup or delivery",
    "choice",
    False,
    ("pickup", "delivery", "either"),
    False,
)
MERCHANDISE_FIELDS: tuple[FieldSeed, ...] = (
    CONDITION,
    ("brand_or_make", "Brand or make", "text", False, (), True),
    ("model", "Model", "text", False, (), True),
    ("color", "Color", "text", False, (), False),
    ("material", "Material", "text", False, (), False),
    ("dimensions", "Dimensions", "text", False, (), False),
    ("quantity", "Quantity", "integer", False, (), False),
    FULFILLMENT,
)
APPAREL_FIELDS: tuple[FieldSeed, ...] = (
    CONDITION,
    ("brand", "Brand", "text", False, (), True),
    ("size", "Size", "text", False, (), True),
    ("color", "Color", "text", False, (), False),
    ("material", "Material", "text", False, (), False),
    ("quantity", "Quantity", "integer", False, (), False),
    FULFILLMENT,
)
COLLECTIBLE_FIELDS: tuple[FieldSeed, ...] = (
    CONDITION,
    ("maker_or_creator", "Maker or creator", "text", False, (), True),
    ("era_or_year", "Era or year", "text", False, (), True),
    ("material", "Material", "text", False, (), False),
    ("dimensions", "Dimensions", "text", False, (), False),
    ("quantity", "Quantity", "integer", False, (), False),
    FULFILLMENT,
)
ELECTRONICS_FIELDS: tuple[FieldSeed, ...] = (
    CONDITION,
    ("brand", "Brand", "text", False, (), True),
    ("model", "Model", "text", False, (), True),
    ("capacity", "Storage or capacity", "text", False, (), True),
    ("compatibility", "Compatibility", "text", False, (), True),
    ("accessories_included", "Accessories included", "boolean", False, (), False),
    FULFILLMENT,
)
SERVICE_FIELDS: tuple[FieldSeed, ...] = (
    ("availability", "Availability", "choice", True, ("weekdays", "weekends", "flexible"), True),
    ("service_format", "Service format", "choice", False, ("on_site", "remote", "either"), False),
    (
        "experience_level",
        "Experience level",
        "choice",
        False,
        ("entry", "experienced", "established"),
        True,
    ),
)
JOB_FIELDS: tuple[FieldSeed, ...] = (
    (
        "employment_type",
        "Employment type",
        "choice",
        True,
        ("full_time", "part_time", "seasonal", "contract"),
        True,
    ),
    ("schedule", "Typical schedule", "text", False, (), False),
    (
        "experience_level",
        "Experience level",
        "choice",
        False,
        ("entry", "experienced", "established"),
        True,
    ),
    ("start_timing", "Start timing", "text", False, (), False),
)
PET_FIELDS: tuple[FieldSeed, ...] = (
    ("breed_or_type", "Breed or type", "text", False, (), True),
    ("age_group", "Age group", "choice", False, ("young", "adult", "senior"), False),
    ("color", "Color", "text", False, (), False),
    ("quantity", "Quantity", "integer", False, (), False),
)
COMMUNITY_FIELDS: tuple[FieldSeed, ...] = (
    (
        "listing_type",
        "Listing type",
        "choice",
        True,
        ("event", "class", "group", "volunteer", "lost_found", "other"),
        True,
    ),
    ("schedule", "Schedule", "text", False, (), False),
    ("age_group", "Age group", "text", False, (), False),
    ("quantity", "Quantity", "integer", False, (), False),
)
SPORTING_FIELDS: tuple[FieldSeed, ...] = (
    *MERCHANDISE_FIELDS[:-2],
    ("activity", "Activity", "text", False, (), True),
    FULFILLMENT,
)
RECREATION_FIELDS: tuple[FieldSeed, ...] = (
    *MERCHANDISE_FIELDS[:-3],
    ("compatibility", "Compatibility", "text", False, (), True),
    FULFILLMENT,
)
TOOL_FIELDS: tuple[FieldSeed, ...] = (
    *MERCHANDISE_FIELDS[:-3],
    ("power_source", "Power source", "text", False, (), False),
    ("compatibility", "Compatibility", "text", False, (), True),
    FULFILLMENT,
)
OTHERS_FIELDS: tuple[FieldSeed, ...] = (
    ("condition", "Condition", "choice", False, ("new", "like_new", "good", "fair"), True),
    ("quantity", "Quantity", "integer", False, (), False),
    FULFILLMENT,
)
VERTICAL_FIELD_ARCHETYPES: dict[str, tuple[FieldSeed, ...]] = {
    "clothing-personal": APPAREL_FIELDS,
    "collectibles-art": COLLECTIBLE_FIELDS,
    "community": COMMUNITY_FIELDS,
    "electronics": ELECTRONICS_FIELDS,
    "jobs": JOB_FIELDS,
    "recreation-hobbies": RECREATION_FIELDS,
    "services": SERVICE_FIELDS,
    "sporting-outdoor": SPORTING_FIELDS,
    "tools-equipment": TOOL_FIELDS,
    "others": OTHERS_FIELDS,
}


def profile_fields_for(*, category: Category) -> tuple[FieldSeed, ...]:
    """Choose a safe, reusable public-fact archetype for a generic leaf."""
    vertical_slug = category.vertical.slug
    parent = category.parent
    if vertical_slug == "livestock-animals" and parent is not None:
        return PET_FIELDS if parent.slug == "pets" else MERCHANDISE_FIELDS
    if vertical_slug == "kids-baby":
        return (
            APPAREL_FIELDS
            if parent is not None and parent.slug == "kids-clothing"
            else MERCHANDISE_FIELDS
        )
    return VERTICAL_FIELD_ARCHETYPES.get(vertical_slug, MERCHANDISE_FIELDS)


@dataclass
class SeedCounts:
    created: int = 0
    updated: int = 0
    unchanged: int = 0

    def record(self, *, created: bool, changed: bool) -> None:
        if created:
            self.created += 1
        elif changed:
            self.updated += 1
        else:
            self.unchanged += 1


class Command(BaseCommand):
    help = "Idempotently seed the versioned marketplace browse taxonomy in DEBUG environments."

    @transaction.atomic
    def handle(self, *_args: object, **_options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_marketplace_catalog may only run with DEBUG enabled.")

        vertical_counts = SeedCounts()
        category_counts = SeedCounts()
        for vertical_seed in MARKETPLACE_CATALOG:
            vertical = self._seed_vertical(vertical_seed, vertical_counts)
            self._seed_categories(vertical, vertical_seed, category_counts)
        profile_counts = self._seed_profiles()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded marketplace catalog {MARKETPLACE_CATALOG_VERSION}: "
                f"{vertical_counts.created} verticals created, {vertical_counts.updated} updated, "
                f"{vertical_counts.unchanged} unchanged; "
                f"{category_counts.created} categories created, {category_counts.updated} updated, "
                f"{category_counts.unchanged} unchanged. "
                f"{profile_counts.created} profiles created, {profile_counts.updated} updated, "
                f"{profile_counts.unchanged} unchanged. "
                "No ListingKinds, products, or prices were created."
            )
        )

    @staticmethod
    def _seed_vertical(seed: VerticalSeed, counts: SeedCounts) -> Vertical:
        defaults = {
            "name": seed.name,
            "display_order": seed.display_order,
            "is_active": True,
        }
        vertical, created = Vertical.objects.get_or_create(slug=seed.slug, defaults=defaults)
        changed = Command._update_seed_owned_fields(vertical, defaults) if not created else False
        counts.record(created=created, changed=changed)
        return vertical

    @staticmethod
    def _seed_categories(
        vertical: Vertical, vertical_seed: VerticalSeed, counts: SeedCounts
    ) -> None:
        seeded_categories: dict[str, Category] = {}
        for category_seed in vertical_seed.categories:
            parent = (
                seeded_categories[category_seed.parent_slug]
                if category_seed.parent_slug is not None
                else None
            )
            category = Command._seed_category(vertical, category_seed, parent, counts)
            seeded_categories[category_seed.slug] = category

    @staticmethod
    def _seed_category(
        vertical: Vertical,
        seed: CategorySeed,
        parent: Category | None,
        counts: SeedCounts,
    ) -> Category:
        defaults = {
            "name": seed.name,
            "parent": parent,
            "display_order": seed.display_order,
            "is_active": True,
        }
        category, created = Category.objects.get_or_create(
            vertical=vertical, slug=seed.slug, defaults=defaults
        )
        changed = Command._update_seed_owned_fields(category, defaults) if not created else False
        counts.record(created=created, changed=changed)
        return category

    @staticmethod
    def _update_seed_owned_fields(
        instance: Vertical | Category | CatalogPostingProfile | CatalogPostingField,
        defaults: Mapping[str, object],
    ) -> bool:
        changed_fields = [
            field_name
            for field_name, value in defaults.items()
            if getattr(instance, field_name) != value
        ]
        if not changed_fields:
            return False
        for field_name in changed_fields:
            setattr(instance, field_name, defaults[field_name])
        instance.save(update_fields=changed_fields)
        return True

    @staticmethod
    def _seed_profiles() -> SeedCounts:
        counts = SeedCounts()
        leaves = Category.objects.filter(is_active=True, vertical__is_active=True).exclude(
            children__is_active=True
        )
        for category in leaves.select_related("vertical", "parent"):
            if resolve_listing_workflow(category=category).typed:
                profile = CatalogPostingProfile.objects.filter(category=category).first()
                if profile is not None:
                    changed = Command._update_seed_owned_fields(profile, {"is_active": False})
                    counts.record(created=False, changed=changed)
                continue
            profile, created = CatalogPostingProfile.objects.get_or_create(
                category=category, defaults={"version": PROFILE_VERSION, "is_active": True}
            )
            changed = (
                Command._update_seed_owned_fields(
                    profile, {"version": PROFILE_VERSION, "is_active": True}
                )
                if not created
                else False
            )
            counts.record(created=created, changed=changed)
            for order, (key, label, field_type, required, choices, searchable) in enumerate(
                profile_fields_for(category=category), start=1
            ):
                defaults = {
                    "label": label,
                    "field_type": field_type,
                    "required": required,
                    "choices": list(choices),
                    "visibility": "public",
                    "display_order": order,
                    "maximum": 120 if field_type == "text" else None,
                    "is_material": True,
                    "allow_public_search": searchable,
                }
                field, field_created = CatalogPostingField.objects.get_or_create(
                    profile=profile,
                    key=key,
                    defaults=defaults,
                )
                if not field_created:
                    Command._update_seed_owned_fields(field, defaults)
        return counts
