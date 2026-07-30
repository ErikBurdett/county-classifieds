from __future__ import annotations

import pytest
from django import forms
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, override_settings
from django.urls import reverse

from apps.accounts.models import SellerProfile, User
from apps.catalog.models import CatalogPostingField, CatalogPostingProfile, Category, Vertical
from apps.listings.forms import (
    AutoListingForm,
    GenericListingForm,
    HomeListingForm,
    ListingCategoryForm,
    ListingTaxonomyAndFactsForm,
    ProfileAttributesForm,
)
from apps.listings.models import GenericListingDetails, HomeDetails, Listing, ListingStatus
from apps.listings.services import replace_listing_taxonomy_and_facts
from apps.listings.workflows import resolve_listing_workflow
from apps.locations.models import County, State, ZipCountyReference

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("vertical_slug", "category_slug", "expected"),
    [
        ("autos", "cars", "auto"),
        ("real-estate", "homes", "home"),
        ("rentals", "apartments", "rental"),
        ("farm-ranch", "tractors", "ag_equipment"),
        ("farm-ranch", "pasture-lease", "pasture"),
        ("livestock-animals", "cattle", "livestock"),
        ("home-garden", "furniture", "home_goods"),
        ("appliances", "washers", "home_goods"),
        ("services", "cleaning", "generic"),
    ],
)
def test_leaf_workflow_resolution(vertical_slug: str, category_slug: str, expected: str) -> None:
    vertical = Vertical.objects.create(name=vertical_slug, slug=vertical_slug)
    category = Category.objects.create(vertical=vertical, name=category_slug, slug=category_slug)

    assert resolve_listing_workflow(category=category).key == expected


def test_category_group_is_not_postable() -> None:
    vertical = Vertical.objects.create(name="Services", slug="services")
    group = Category.objects.create(vertical=vertical, name="Home", slug="home")
    Category.objects.create(vertical=vertical, parent=group, name="Cleaning", slug="cleaning")

    with pytest.raises(ValueError):
        resolve_listing_workflow(category=group)


def test_generic_attributes_reject_unknown_profile_key() -> None:
    vertical = Vertical.objects.create(name="Services", slug="services")
    category = Category.objects.create(vertical=vertical, name="Cleaning", slug="cleaning")
    profile = CatalogPostingProfile.objects.create(category=category)
    CatalogPostingField.objects.create(
        profile=profile,
        key="availability",
        label="Availability",
        field_type="choice",
        choices=["weekdays"],
        allow_public_search=True,
    )
    assert profile.fields.get(key="availability").allow_public_search
    assert GenericListingDetails._meta.get_field("attributes").default is dict

    with pytest.raises(ValidationError):
        CatalogPostingField(
            profile=profile,
            key="private_note",
            label="Private note",
            field_type="text",
            visibility="staff_only",
            allow_public_search=True,
        ).full_clean()


def test_profile_attributes_form_enforces_catalog_choices_and_limits() -> None:
    vertical = Vertical.objects.create(name="Services", slug="services")
    category = Category.objects.create(vertical=vertical, name="Cleaning", slug="cleaning")
    profile = CatalogPostingProfile.objects.create(category=category)
    CatalogPostingField.objects.create(
        profile=profile,
        key="availability",
        label="Availability",
        field_type="choice",
        required=True,
        choices=["weekdays", "weekends"],
    )
    CatalogPostingField.objects.create(
        profile=profile,
        key="years_experience",
        label="Years of experience",
        field_type="integer",
        maximum=50,
    )

    valid = ProfileAttributesForm(
        {"availability": "weekdays", "years_experience": "12"}, profile=profile
    )
    invalid = ProfileAttributesForm(
        {"availability": "always", "years_experience": "51"}, profile=profile
    )
    stale = ProfileAttributesForm(
        {"availability": "weekdays", "attribute_retired": "x"}, profile=profile
    )

    assert valid.is_valid()
    assert valid.cleaned_data == {"availability": "weekdays", "years_experience": 12}
    assert not invalid.is_valid()
    assert {"availability", "years_experience"} <= set(invalid.errors)
    assert not stale.is_valid()


@pytest.fixture
def unified_reference() -> tuple[SellerProfile, State, County]:
    user = User.objects.create_user(email="unified@example.com", password="password")
    seller = SellerProfile.objects.create(user=user, display_name="Unified seller")
    state = State.objects.create(
        fips="48", usps_code="TX", name="Texas", slug="texas", is_active=True
    )
    county = County.objects.create(
        fips="48375", state=state, name="Potter", slug="potter", is_active=True
    )
    ZipCountyReference.objects.create(
        postal_code="79101",
        county=county,
        source_name="test",
        source_url="https://example.test",
        release_version="test",
        release_date="2026-07-29",
        sha256_checksum="0" * 64,
        transformation_version="test",
    )
    return seller, state, county


def test_unified_route_advances_then_creates_home_details(
    client: Client, unified_reference: tuple[SellerProfile, State, County]
) -> None:
    seller, state, county = unified_reference
    vertical = Vertical.objects.create(name="Real Estate", slug="real-estate")
    category = Category.objects.create(vertical=vertical, name="Homes", slug="homes")
    client.force_login(seller.user)

    advance = client.post(
        reverse("listings:create_listing"),
        {"vertical": vertical.id, "category": category.id},
    )
    assert advance.status_code == 200
    assert b"Property type" in advance.content
    response = client.post(
        reverse("listings:create_listing"),
        {
            "typed_workflow": "1",
            "vertical": vertical.id,
            "category": category.id,
            "state": state.id,
            "county": county.id,
            "city": "Amarillo",
            "title": "Three bedroom home",
            "description": "Well maintained home.",
            "broker_name": "  Panhandle   Property Group  ",
            "price_minor": 25000000,
            "currency": "USD",
            "property_type": "house",
            "beds": 3,
            "baths": "2.0",
            "square_feet": 1800,
            "general_area": "North Amarillo",
        },
    )
    assert response.status_code == 302, response.content.decode()
    listing = Listing.objects.get(title="Three bedroom home")
    assert listing.category == category
    assert listing.broker_name == "Panhandle Property Group"
    assert HomeDetails.objects.get(listing=listing).beds == 3
    assert not hasattr(listing, "generic_details")


def test_unified_typed_advance_preserves_common_values_without_creating_draft(
    client: Client, unified_reference: tuple[SellerProfile, State, County]
) -> None:
    seller, state, county = unified_reference
    vertical = Vertical.objects.create(name="Real Estate", slug="real-estate")
    category = Category.objects.create(vertical=vertical, name="Homes", slug="homes")
    secondary = Category.objects.create(vertical=vertical, name="Land", slug="land")
    client.force_login(seller.user)

    response = client.post(
        reverse("listings:create_listing"),
        {
            "show_fields": "1",
            "vertical": vertical.id,
            "category": category.id,
            "state": state.id,
            "county": county.id,
            "city": "Amarillo",
            "title": "Preserved home",
            "description": "Preserved description.",
            "price_mode": "fixed",
            "asking_price": "250000.00",
            "broker_name": "Panhandle Realty",
            "controlled_tags": [secondary.id],
            "seller_tag_0": "Open house",
            "custom_field_label_0": "School district",
            "custom_field_value_0": "West",
        },
    )

    assert response.status_code == 200
    assert Listing.objects.count() == 0
    assert response.context["listing_form"].is_bound
    assert response.context["listing_form"]["title"].value() == "Preserved home"
    assert response.context["listing_form"]["price_minor"].value() == "25000000"
    assert response.context["listing_form"]["broker_name"].value() == "Panhandle Realty"
    assert response.context["taxonomy_form"]["seller_tag_0"].value() == "Open house"
    assert response.context["taxonomy_form"]["custom_field_value_0"].value() == "West"
    assert response.context["taxonomy_form"]["controlled_tags"].value() == [str(secondary.id)]
    assert b"List on Nearby Counties" not in response.content


def test_unified_generic_advance_preserves_profile_county_price_and_facts(
    client: Client, unified_reference: tuple[SellerProfile, State, County]
) -> None:
    seller, state, county = unified_reference
    extra_county = County.objects.create(
        fips="48113", state=state, name="Dallas", slug="dallas", is_active=True
    )
    ZipCountyReference.objects.create(
        postal_code="79101",
        county=extra_county,
        source_name="test",
        source_url="https://example.test",
        release_version="test",
        release_date="2026-07-30",
        sha256_checksum="1" * 64,
        transformation_version="test",
    )
    vertical = Vertical.objects.create(name="Services", slug="services")
    category = Category.objects.create(vertical=vertical, name="Cleaning", slug="cleaning")
    secondary = Category.objects.create(vertical=vertical, name="Commercial", slug="commercial")
    profile = CatalogPostingProfile.objects.create(category=category)
    CatalogPostingField.objects.create(
        profile=profile,
        key="availability",
        label="Availability",
        field_type="choice",
        choices=["weekdays"],
    )
    client.force_login(seller.user)

    response = client.post(
        reverse("listings:create_listing"),
        {
            "show_fields": "1",
            "vertical": vertical.id,
            "category": category.id,
            "state": state.id,
            "county": county.id,
            "additional_counties": [extra_county.id],
            "city": "Amarillo",
            "title": "Preserved service",
            "description": "Preserved description.",
            "price_mode": "fixed",
            "asking_price": "25.00",
            "postal_code": "79101",
            "street_address": "1 Private Way",
            "availability": "weekdays",
            "controlled_tags": [secondary.id],
            "seller_tag_0": "Weekend",
            "custom_field_label_0": "Coverage",
            "custom_field_value_0": "Weekends",
        },
    )

    assert response.status_code == 200
    assert Listing.objects.count() == 0
    assert response.context["listing_form"].is_bound
    assert response.context["listing_form"]["additional_counties"].value() == [str(extra_county.id)]
    assert response.context["listing_form"]["asking_price"].value() == "25.00"
    assert response.context["listing_form"]["street_address"].value() == "1 Private Way"
    assert response.context["profile_form"]["availability"].value() == "weekdays"
    assert response.context["taxonomy_form"]["seller_tag_0"].value() == "Weekend"


def test_unified_create_entry_starts_with_common_listing_controls(
    client: Client, unified_reference: tuple[SellerProfile, State, County]
) -> None:
    seller, _state, _county = unified_reference
    client.force_login(seller.user)

    response = client.get(reverse("listings:create_listing"))

    assert response.status_code == 200
    assert b'action="/dashboard/listings/new/"' in response.content
    assert b"Postal / ZIP code" in response.content
    assert b'data-unified-create="true"' in response.content


def test_unified_category_choices_are_scoped_to_selected_vertical() -> None:
    community = Vertical.objects.create(name="Community", slug="community")
    merchandise = Vertical.objects.create(name="Merchandise", slug="merchandise")
    community_category = Category.objects.create(vertical=community, name="Events", slug="events")
    other_category = Category.objects.create(vertical=merchandise, name="Shoes", slug="shoes")

    form = ListingCategoryForm({"vertical": community.id, "category": other_category.id})

    category_field = form.fields["category"]
    assert isinstance(category_field, forms.ModelChoiceField)
    assert category_field.queryset is not None
    assert list(category_field.queryset) == [community_category]
    assert not form.is_valid()
    assert "category" in form.errors


def test_category_selector_exposes_only_leaves_with_hierarchy_labels(client: Client) -> None:
    vertical = Vertical.objects.create(name="Clothing & Personal", slug="clothing-personal")
    group = Category.objects.create(vertical=vertical, name="Shoes & Accessories", slug="shoes")
    leaf = Category.objects.create(vertical=vertical, parent=group, name="Shoes", slug="shoes-leaf")
    other = Category.objects.create(vertical=vertical, name="Other", slug="other")
    user = User.objects.create_user(email="category-selector@example.com", password="password")
    SellerProfile.objects.create(user=user, display_name="Category selector")
    client.force_login(user)

    form = ListingCategoryForm({"vertical": vertical.id, "category": group.id})
    category_field = form.fields["category"]
    assert isinstance(category_field, forms.ModelChoiceField)
    category_queryset = category_field.queryset
    assert category_queryset is not None
    categories = list(category_queryset)
    response = client.get(reverse("listings:generic_categories"), {"vertical": vertical.id})

    assert {category.id for category in categories} == {leaf.id, other.id}
    assert {category_field.label_from_instance(category) for category in categories} == {
        "Clothing & Personal \u203a Shoes & Accessories \u203a Shoes",
        "Clothing & Personal \u203a Other",
    }
    assert not form.is_valid()
    assert form.errors["category"] == ["Choose a postable subcategory, not a category group."]
    assert response.json()["categories"] == [
        {"id": other.id, "name": "Clothing & Personal \u203a Other"},
        {"id": leaf.id, "name": "Clothing & Personal \u203a Shoes & Accessories \u203a Shoes"},
    ]


def test_authenticated_location_candidates_are_active_only_and_state_scoped(
    client: Client, unified_reference: tuple[SellerProfile, State, County]
) -> None:
    seller, state, county = unified_reference
    inactive_state = State.objects.create(
        fips="01", usps_code="AL", name="Alabama", slug="alabama", is_active=False
    )
    County.objects.create(
        fips="01001", state=inactive_state, name="Autauga", slug="autauga", is_active=True
    )
    County.objects.create(
        fips="48113", state=state, name="Inactive", slug="inactive", is_active=False
    )

    assert client.get(reverse("listings:state_candidates"), {"q": "Texas"}).status_code == 302
    assert (
        client.get(
            reverse("listings:generic_county_candidates"), {"state": str(state.id)}
        ).status_code
        == 302
    )
    client.force_login(seller.user)

    states = client.get(reverse("listings:state_candidates"), {"q": "a"}).json()["states"]
    counties = client.get(
        reverse("listings:generic_county_candidates"), {"state": str(state.id), "q": "Pot"}
    ).json()["counties"]

    assert states == [{"id": state.id, "name": "Texas", "code": "TX"}]
    assert counties == [{"id": county.id, "name": "Potter", "verified": False}]


def test_unified_no_javascript_group_submission_has_clear_error(
    client: Client, unified_reference: tuple[SellerProfile, State, County]
) -> None:
    seller, _state, _county = unified_reference
    vertical = Vertical.objects.create(name="Services", slug="services")
    group = Category.objects.create(vertical=vertical, name="Home Services", slug="home-services")
    Category.objects.create(vertical=vertical, parent=group, name="Cleaning", slug="cleaning")
    client.force_login(seller.user)

    response = client.post(
        reverse("listings:create_listing"),
        {"vertical": vertical.id, "category": group.id, "show_fields": "1"},
    )

    assert response.status_code == 200
    assert b"Choose a postable subcategory, not a category group." in response.content
    assert b"Fields for" not in response.content


def test_unified_others_no_javascript_resolves_general_and_requires_a_seller_tag(
    client: Client, unified_reference: tuple[SellerProfile, State, County]
) -> None:
    seller, state, county = unified_reference
    vertical = Vertical.objects.create(name="Others", slug="others")
    general = Category.objects.create(vertical=vertical, name="General", slug="general")
    client.force_login(seller.user)

    advance = client.post(
        reverse("listings:create_listing"),
        {"vertical": vertical.id, "show_fields": "1"},
    )

    assert advance.status_code == 200
    assert advance.context["selected_category"] == general
    assert b'id="id_category"' not in advance.content
    assert b"Add at least one plain-text tag to classify this Others listing." in advance.content

    missing_tag = client.post(
        reverse("listings:create_listing"),
        {
            "vertical": vertical.id,
            "state": state.id,
            "county": county.id,
            "city": "Amarillo",
            "title": "Unclassified other",
            "description": "Safe description.",
            "price_mode": "contact",
            "postal_code": "79101",
        },
    )
    assert missing_tag.status_code == 200
    assert Listing.objects.count() == 0
    assert b"This field is required." in missing_tag.content

    created = client.post(
        reverse("listings:create_listing"),
        {
            "vertical": vertical.id,
            "state": state.id,
            "county": county.id,
            "city": "Amarillo",
            "title": "Tagged other",
            "description": "Safe description.",
            "price_mode": "contact",
            "postal_code": "79101",
            "seller_tag_0": "Workshop supplies",
        },
    )
    assert created.status_code == 302, created.content.decode()
    listing = Listing.objects.get(title="Tagged other")
    assert listing.category == general
    assert list(listing.seller_tags.values_list("value", flat=True)) == ["Workshop supplies"]


@override_settings(DEBUG=True)
def test_seeded_profile_fields_cover_every_generic_leaf_and_not_typed_leaves() -> None:
    call_command("seed_marketplace_catalog")
    leaves = Category.objects.filter(is_active=True, vertical__is_active=True).exclude(
        children__is_active=True
    )

    for vertical in Vertical.objects.order_by("display_order"):
        vertical_leaves = list(
            leaves.filter(vertical=vertical).select_related("vertical", "parent").order_by("slug")
        )
        assert vertical_leaves
        for category in vertical_leaves:
            workflow = resolve_listing_workflow(category=category)
            profile = CatalogPostingProfile.objects.filter(
                category=category, is_active=True
            ).first()
            if workflow.typed:
                assert profile is None
            else:
                assert profile is not None
                assert profile.fields.exists()


def test_unified_catalog_profile_creates_bounded_generic_attributes(
    client: Client, unified_reference: tuple[SellerProfile, State, County]
) -> None:
    seller, state, county = unified_reference
    vertical = Vertical.objects.create(name="Services", slug="services")
    category = Category.objects.create(vertical=vertical, name="Cleaning", slug="cleaning")
    profile = CatalogPostingProfile.objects.create(category=category, version=3)
    CatalogPostingField.objects.create(
        profile=profile,
        key="availability",
        label="Availability",
        field_type="choice",
        required=True,
        choices=["weekdays", "weekends"],
        allow_public_search=True,
    )
    client.force_login(seller.user)

    response = client.post(
        reverse("listings:create_listing"),
        {
            "vertical": vertical.id,
            "category": category.id,
            "state": state.id,
            "county": county.id,
            "city": "Amarillo",
            "title": "Reliable cleaning",
            "description": "Residential cleaning service.",
            "price_mode": "contact",
            "postal_code": "79101",
            "street_address": "",
            "availability": "weekdays",
        },
    )
    assert response.status_code == 302, response.content.decode()
    details = GenericListingDetails.objects.get(listing__title="Reliable cleaning")
    assert details.schema_version == 3
    assert details.attributes == {"availability": "weekdays"}


def test_broker_attribution_forms_allow_only_approved_verticals(
    unified_reference: tuple[SellerProfile, State, County],
) -> None:
    _seller, state, county = unified_reference
    homes = Vertical.objects.create(name="Real Estate", slug="real-estate")
    home_category = Category.objects.create(vertical=homes, name="Homes", slug="homes")
    autos = Vertical.objects.create(name="Autos", slug="autos")
    auto_category = Category.objects.create(vertical=autos, name="Cars", slug="cars")

    home_form = HomeListingForm(
        {
            "category": home_category.id,
            "state": state.id,
            "county": county.id,
            "city": "Amarillo",
            "title": "Home",
            "description": "Description",
            "broker_name": "Example Realty",
            "price_minor": 1,
            "currency": "USD",
        }
    )
    forged_auto_form = AutoListingForm(
        {
            "category": auto_category.id,
            "state": state.id,
            "county": county.id,
            "city": "Amarillo",
            "title": "Auto",
            "description": "Description",
            "broker_name": "Forged Realty",
            "price_minor": 1,
            "currency": "USD",
        }
    )
    generic_auto_form = GenericListingForm(
        {
            "vertical": autos.id,
            "category": auto_category.id,
            "state": state.id,
            "county": county.id,
            "city": "Amarillo",
            "title": "Auto",
            "description": "Description",
            "broker_name": "Forged Realty",
            "price_mode": "contact",
            "postal_code": "79101",
        }
    )

    assert "broker_name" in home_form.fields
    assert home_form.is_valid(), home_form.errors
    assert "broker_name" not in forged_auto_form.fields
    assert not forged_auto_form.is_valid()
    assert "Broker attribution" in forged_auto_form.non_field_errors().as_text()
    assert "broker_name" not in generic_auto_form.fields
    assert not generic_auto_form.is_valid()
    assert "Broker attribution" in generic_auto_form.non_field_errors().as_text()


def test_listing_broker_name_field_is_bounded_and_optional() -> None:
    field = Listing._meta.get_field("broker_name")

    assert field.blank
    assert field.max_length == 120


def test_taxonomy_and_fact_form_normalizes_and_rejects_private_input(
    unified_reference: tuple[SellerProfile, State, County],
) -> None:
    _seller, _state, _county = unified_reference
    vertical = Vertical.objects.create(name="Services", slug="services")
    primary = Category.objects.create(vertical=vertical, name="Cleaning", slug="cleaning")
    controlled = Category.objects.create(vertical=vertical, name="Commercial", slug="commercial")
    form = ListingTaxonomyAndFactsForm(
        {
            "controlled_tags": [controlled.id],
            "seller_tag_0": "  Weekend   service ",
            "seller_tag_1": "weekend service",
            "seller_tag_2": "https://unsafe.example",
            "custom_field_label_0": "Coverage",
            "custom_field_value_0": "Weekends",
            "custom_field_label_1": "Contact",
            "custom_field_value_1": "555 555 5555",
        },
        vertical=vertical,
        primary_category=primary,
    )

    assert not form.is_valid()
    assert "unique" in form.non_field_errors().as_text().lower()
    assert "contact" in form.non_field_errors().as_text().lower()


def test_published_taxonomy_fact_edit_returns_listing_to_review(
    unified_reference: tuple[SellerProfile, State, County],
) -> None:
    seller, state, county = unified_reference
    vertical = Vertical.objects.create(name="Autos", slug="autos")
    primary = Category.objects.create(vertical=vertical, name="Cars", slug="cars")
    secondary = Category.objects.create(vertical=vertical, name="Convertibles", slug="convertibles")
    listing = Listing.objects.create(
        seller=seller,
        vertical=vertical,
        category=primary,
        state=state,
        county=county,
        city="Amarillo",
        title="Published",
        description="Description",
        status=ListingStatus.PUBLISHED,
        published_at="2026-07-29T00:00:00Z",
    )

    edited = replace_listing_taxonomy_and_facts(
        listing_id=listing.id,
        seller=seller,
        controlled_categories=[secondary],
        seller_tags=["Summer sale"],
        custom_fields=[{"label": "Color", "value": "Blue"}],
    )

    assert edited.status == ListingStatus.IN_REVIEW
    assert not edited.published_at
    assert list(edited.seller_tags.values_list("value", flat=True)) == ["Summer sale"]
    assert list(edited.custom_fields.values_list("label", flat=True)) == ["Color"]


def test_unified_edit_updates_typed_details_taxonomy_and_broker(
    client: Client, unified_reference: tuple[SellerProfile, State, County]
) -> None:
    seller, state, county = unified_reference
    vertical = Vertical.objects.create(name="Real Estate", slug="real-estate")
    category = Category.objects.create(vertical=vertical, name="Homes", slug="homes")
    secondary = Category.objects.create(vertical=vertical, name="Land", slug="land")
    listing = Listing.objects.create(
        seller=seller,
        vertical=vertical,
        category=category,
        state=state,
        county=county,
        city="Amarillo",
        title="Original home",
        description="Original description",
        broker_name="Original Realty",
        price_minor=25000000,
        currency="USD",
    )
    HomeDetails.objects.create(
        listing=listing,
        property_type="house",
        beds=3,
        baths="2.0",
        square_feet=1800,
        general_area="North Amarillo",
    )
    client.force_login(seller.user)

    response = client.post(
        reverse("listings:edit_listing", kwargs={"listing_id": listing.id}),
        {
            "category": category.id,
            "state": state.id,
            "county": county.id,
            "city": "Amarillo",
            "title": "Updated home",
            "description": "Updated description",
            "broker_name": "Updated Realty",
            "price_minor": 26000000,
            "currency": "USD",
            "property_type": "house",
            "beds": 4,
            "baths": "3.0",
            "square_feet": 2200,
            "general_area": "North Amarillo",
            "controlled_tags": [secondary.id],
            "seller_tag_0": "Open house",
            "custom_field_label_0": "School district",
            "custom_field_value_0": "West",
        },
    )

    assert response.status_code == 302, response.content.decode()
    listing.refresh_from_db()
    assert listing.title == "Updated home"
    assert listing.broker_name == "Updated Realty"
    assert listing.home_details.beds == 4
    assert not GenericListingDetails.objects.filter(listing=listing).exists()
    assert set(listing.controlled_tags.values_list("category", flat=True)) == {
        category.id,
        secondary.id,
    }
    assert list(listing.seller_tags.values_list("value", flat=True)) == ["Open house"]
    assert list(listing.custom_fields.values_list("label", flat=True)) == ["School district"]


def test_unified_edit_blocks_non_owner_and_reviewed_listing(
    client: Client, unified_reference: tuple[SellerProfile, State, County]
) -> None:
    seller, state, county = unified_reference
    vertical = Vertical.objects.create(name="Services", slug="services")
    category = Category.objects.create(vertical=vertical, name="Cleaning", slug="cleaning")
    profile = CatalogPostingProfile.objects.create(category=category, version=2)
    CatalogPostingField.objects.create(
        profile=profile,
        key="availability",
        label="Availability",
        field_type="choice",
        required=True,
        choices=["weekdays"],
    )
    listing = Listing.objects.create(
        seller=seller,
        vertical=vertical,
        category=category,
        state=state,
        county=county,
        city="Amarillo",
        title="Private service",
        description="Description",
    )
    GenericListingDetails.objects.create(
        listing=listing,
        price_mode="contact",
        postal_code="79101",
        schema_version=2,
        attributes={"availability": "weekdays"},
    )
    other = User.objects.create_user(email="other-owner@example.com", password="password")
    SellerProfile.objects.create(user=other, display_name="Other owner")
    client.force_login(other)

    assert (
        client.get(reverse("listings:edit_listing", kwargs={"listing_id": listing.id})).status_code
        == 404
    )

    client.force_login(seller.user)
    listing.status = ListingStatus.IN_REVIEW
    listing.save(update_fields=("status", "updated_at"))
    response = client.post(
        reverse("listings:edit_listing", kwargs={"listing_id": listing.id}),
        {
            "vertical": vertical.id,
            "category": category.id,
            "state": state.id,
            "county": county.id,
            "city": "Amarillo",
            "title": "Attempted update",
            "description": "Description",
            "price_mode": "contact",
            "postal_code": "79101",
            "availability": "weekdays",
        },
    )

    assert response.status_code == 403
    listing.refresh_from_db()
    assert listing.title == "Private service"


def test_unified_published_generic_edit_removes_public_visibility(
    client: Client, unified_reference: tuple[SellerProfile, State, County]
) -> None:
    seller, state, county = unified_reference
    state.is_network_enabled = True
    state.save(update_fields=("is_network_enabled",))
    county.is_network_enabled = True
    county.save(update_fields=("is_network_enabled",))
    vertical = Vertical.objects.create(name="Services", slug="services")
    category = Category.objects.create(vertical=vertical, name="Cleaning", slug="cleaning")
    listing = Listing.objects.create(
        seller=seller,
        vertical=vertical,
        category=category,
        state=state,
        county=county,
        city="Amarillo",
        title="Published service",
        description="Description",
        status=ListingStatus.PUBLISHED,
        published_at="2026-07-30T00:00:00Z",
    )
    GenericListingDetails.objects.create(
        listing=listing,
        price_mode="contact",
        postal_code="79101",
    )
    client.force_login(seller.user)

    response = client.post(
        reverse("listings:edit_listing", kwargs={"listing_id": listing.id}),
        {
            "vertical": vertical.id,
            "state": state.id,
            "county": county.id,
            "city": "Amarillo",
            "title": "Edited published service",
            "description": "Changed description",
            "price_mode": "contact",
            "postal_code": "79101",
            "seller_tag_0": "Weekend",
        },
    )

    assert response.status_code == 302
    listing.refresh_from_db()
    assert listing.status == ListingStatus.IN_REVIEW
    assert listing.published_at is None
    public = client.get(
        reverse(
            "locations:listing_detail",
            kwargs={
                "state_slug": state.slug,
                "county_slug": county.slug,
                "listing_id": listing.id,
            },
        )
    )
    assert public.status_code == 404
