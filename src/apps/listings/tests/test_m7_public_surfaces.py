from __future__ import annotations

from datetime import timedelta
from io import BytesIO
from unittest.mock import Mock

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.http import Http404
from django.test import Client
from django.test.utils import override_settings
from django.utils import timezone

from apps.accounts.models import AccountStatus, SellerProfile, User
from apps.catalog.models import Category, Vertical
from apps.listings.models import (
    Listing,
    ListingImage,
    ListingImageModerationStatus,
    ListingImageState,
    ListingStatus,
    UploadSession,
)
from apps.listings.presenters import present_public_listing
from apps.listings.search import public_search_terms
from apps.listings.selectors import (
    public_listing_for_location,
    public_listing_with_images,
    public_seller_feed_listings,
)
from apps.listings.services import (
    create_auto_draft,
    publish_auto_listing,
    toggle_favorite,
    transition_owned_listing,
    update_auto_draft,
    update_home_draft,
)
from apps.locations.forms import PublicBrowseForm, apply_public_filters
from apps.locations.models import County, State

pytestmark = pytest.mark.django_db


@pytest.fixture
def public_auto() -> Listing:
    seller = SellerProfile.objects.create(
        user=User.objects.create_user(email="m7-public@example.test", password="not-used"),
        display_name="M7 public seller",
    )
    autos = Vertical.objects.create(name="Autos", slug="autos")
    category = Category.objects.create(vertical=autos, name="Cars", slug="cars")
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
    listing = create_auto_draft(
        seller=seller,
        listing_values={
            "category": category,
            "state": state,
            "county": county,
            "city": "Amarillo",
            "title": "Public Mustang",
            "description": "A public listing description.",
            "price_minor": 3_000_000,
            "currency": "USD",
        },
        auto_values={
            "vehicle_type": "car",
            "year": 2020,
            "make": "Ford",
            "model": "Mustang",
            "trim": "",
            "mileage": 12_000,
            "title_status": "clean",
            "vin": "1HGCM82633A004352",
        },
    )
    return publish_auto_listing(listing_id=listing.id)


def test_public_detail_is_canonical_and_never_exposes_vin_or_seller_data(
    client: Client, public_auto: Listing
) -> None:
    response = client.get(f"/texas/potter/listing/{public_auto.id}/")
    canonical = client.get(f"/TEXAS/POTTER/listing/{public_auto.id}/?ref=card&page=1")

    assert response.status_code == 200
    assert b"Public Mustang" in response.content
    assert b"1HGCM82633A004352" not in response.content
    assert b"m7-public@example.test" not in response.content
    assert b'<link rel="canonical"' in response.content
    assert (
        b'<meta property="og:title" content="Public Mustang | TheCountyPost Market">'
        in response.content
    )
    assert (
        b'<meta property="og:url" '
        + f'content="http://testserver/texas/potter/listing/{public_auto.id}/">'.encode()
        in response.content
    )
    assert b'<meta property="og:image"' not in response.content
    assert b'<meta name="twitter:card" content="summary">' in response.content
    assert b'<article class="listing-detail">' in response.content
    assert b'class="listing-gallery listing-gallery--empty"' in response.content
    assert b"Report this listing" in response.content
    assert b"Save listing" not in response.content
    assert (
        b"https://www.google.com/maps/search/?api=1&amp;query=Amarillo%2C%20Potter%2C%20TX"
        in response.content
    )
    assert (
        b"https://www.google.com/maps/dir/?api=1&amp;destination=Amarillo%2C%20Potter%2C%20TX"
        in response.content
    )
    assert (
        b"https://www.google.com/maps?q=Amarillo%2C%20Potter%2C%20TX&amp;output=embed"
        in response.content
    )
    assert b'title="Google Maps map for Amarillo, Potter, TX"' in response.content
    assert b'loading="lazy"' in response.content
    assert b'referrerpolicy="no-referrer"' in response.content
    assert b"This map is provided by Google." in response.content
    assert b'target="_blank" rel="noopener noreferrer"' in response.content
    assert b"opens in a new tab" in response.content
    assert canonical.status_code == 301
    assert canonical["Location"] == f"/texas/potter/listing/{public_auto.id}/?ref=card"

    client.force_login(public_auto.seller.user)
    authenticated = client.get(f"/texas/potter/listing/{public_auto.id}/")
    assert b"Save listing" in authenticated.content


def test_public_detail_hides_nonpublic_and_wrong_location_records(
    client: Client, public_auto: Listing
) -> None:
    public_auto.status = ListingStatus.DRAFT
    public_auto.published_at = None
    public_auto.save(update_fields=("status", "published_at"))

    assert client.get(f"/texas/potter/listing/{public_auto.id}/").status_code == 404
    assert client.get(f"/texas/other/listing/{public_auto.id}/").status_code == 404
    assert (
        b'<meta property="og:title"'
        not in client.get(f"/texas/potter/listing/{public_auto.id}/").content
    )


def test_expired_public_status_is_hidden_before_scheduler_runs(public_auto: Listing) -> None:
    public_auto.expires_at = timezone.now() - timedelta(seconds=1)
    public_auto.save(update_fields=("expires_at",))

    assert not public_listing_with_images().filter(pk=public_auto.pk).exists()


def test_seller_feed_includes_recent_sold_listings_and_respects_visibility_requirements(
    public_auto: Listing,
) -> None:
    first_published_at = public_auto.first_published_at

    sold = transition_owned_listing(
        listing_id=public_auto.id,
        seller=public_auto.seller,
        action="sold",
    )

    assert sold.sold_at is not None
    assert sold.sold_public_until == sold.sold_at + timedelta(days=30)
    assert sold.first_published_at == first_published_at
    assert list(public_seller_feed_listings(seller=public_auto.seller)) == [sold]
    assert not public_listing_with_images().filter(pk=sold.pk).exists()

    sold.sold_public_until = timezone.now() - timedelta(seconds=1)
    sold.save(update_fields=("sold_public_until",))
    assert not public_seller_feed_listings(seller=public_auto.seller).exists()

    sold.sold_public_until = timezone.now() + timedelta(days=1)
    sold.save(update_fields=("sold_public_until",))
    seller_user = public_auto.seller.user
    seller_user.account_status = AccountStatus.SUSPENDED
    seller_user.is_active = False
    seller_user.save(update_fields=("account_status", "is_active"))
    assert not public_seller_feed_listings(seller=public_auto.seller).exists()


def test_sold_listing_retention_cleanup_is_idempotent(public_auto: Listing) -> None:
    sold = transition_owned_listing(
        listing_id=public_auto.id,
        seller=public_auto.seller,
        action="sold",
    )
    sold.sold_public_until = timezone.now() - timedelta(seconds=1)
    sold.save(update_fields=("sold_public_until",))

    call_command("clear_expired_sold_publication")
    call_command("clear_expired_sold_publication")
    sold.refresh_from_db()

    assert sold.sold_public_until is None


def test_first_publication_timestamp_is_retained_after_republication(public_auto: Listing) -> None:
    first_published_at = public_auto.first_published_at
    transition_owned_listing(listing_id=public_auto.id, seller=public_auto.seller, action="sold")
    transition_owned_listing(listing_id=public_auto.id, seller=public_auto.seller, action="archive")
    transition_owned_listing(
        listing_id=public_auto.id,
        seller=public_auto.seller,
        action="restore_draft",
    )

    republished = publish_auto_listing(listing_id=public_auto.id)

    assert republished.published_at is not None
    assert republished.first_published_at == first_published_at


def test_favorites_and_owner_lifecycle_never_bypass_public_visibility(public_auto: Listing) -> None:
    viewer = User.objects.create_user(email="viewer@example.test", password="not-used")

    assert toggle_favorite(listing_id=public_auto.id, user=viewer)
    assert not toggle_favorite(listing_id=public_auto.id, user=viewer)
    assert toggle_favorite(listing_id=public_auto.id, user=viewer)
    transition_owned_listing(listing_id=public_auto.id, seller=public_auto.seller, action="sold")

    assert not public_listing_with_images().filter(pk=public_auto.pk).exists()
    with pytest.raises(ValidationError):
        toggle_favorite(listing_id=public_auto.id, user=viewer)


def test_material_edit_depublishes_and_records_review(public_auto: Listing) -> None:
    details = public_auto.auto_details
    updated = update_auto_draft(
        listing_id=public_auto.id,
        seller=public_auto.seller,
        listing_values={
            "category": public_auto.category,
            "state": public_auto.state,
            "county": public_auto.county,
            "city": public_auto.city,
            "title": "Updated public Mustang",
            "description": public_auto.description,
            "price_minor": public_auto.price_minor,
            "currency": public_auto.currency,
        },
        auto_values={
            "vehicle_type": details.vehicle_type,
            "year": details.year,
            "make": details.make,
            "model": details.model,
            "trim": details.trim,
            "mileage": details.mileage,
            "title_status": details.title_status,
            "vin": details.vin,
        },
    )

    assert updated.status == ListingStatus.IN_REVIEW
    assert updated.published_at is None
    assert not public_listing_with_images().filter(pk=public_auto.pk).exists()


def test_public_selector_returns_only_ready_images_and_generic_404(public_auto: Listing) -> None:
    ready_upload = UploadSession.objects.create(
        listing=public_auto,
        seller=public_auto.seller,
        expires_at=timezone.now() + timedelta(hours=1),
    )
    ready = ListingImage.objects.create(
        listing=public_auto,
        upload_session=ready_upload,
        ordering=1,
        state=ListingImageState.READY,
        moderation_status=ListingImageModerationStatus.APPROVED,
        content_type="image/jpeg",
        byte_size=1,
        width=1,
        height=1,
        storage_key="private/ready.jpg",
        rendition_key="public/ready.jpg",
        original_filename="ready.jpg",
    )
    deleted_upload = UploadSession.objects.create(
        listing=public_auto,
        seller=public_auto.seller,
        expires_at=timezone.now() + timedelta(hours=1),
    )
    ListingImage.objects.create(
        listing=public_auto,
        upload_session=deleted_upload,
        ordering=2,
        state=ListingImageState.DELETED,
        content_type="image/jpeg",
        byte_size=1,
        width=1,
        height=1,
        storage_key="private/deleted.jpg",
        rendition_key="public/deleted.jpg",
        original_filename="deleted.jpg",
    )

    listing = public_listing_with_images().get(pk=public_auto.pk)
    assert list(listing.images.values_list("id", flat=True)) == [ready.id]
    with pytest.raises(Http404, match="Listing not found"):
        public_listing_for_location(
            listing_id=public_auto.id, state_slug="texas", county_slug="other"
        )


def test_public_image_endpoint_allows_only_public_ready_renditions(
    client: Client, monkeypatch: pytest.MonkeyPatch, public_auto: Listing
) -> None:
    upload = UploadSession.objects.create(
        listing=public_auto,
        seller=public_auto.seller,
        expires_at=timezone.now() + timedelta(hours=1),
    )
    image = ListingImage.objects.create(
        listing=public_auto,
        upload_session=upload,
        ordering=1,
        state=ListingImageState.READY,
        moderation_status=ListingImageModerationStatus.APPROVED,
        content_type="image/jpeg",
        byte_size=1,
        width=1,
        height=1,
        storage_key="private/full.jpg",
        rendition_key="public/preview.jpg",
        original_filename="preview.jpg",
    )
    storage_open = Mock(return_value=BytesIO(b"x"))
    monkeypatch.setattr("apps.locations.views.default_storage.open", storage_open)

    response = client.get(f"/images/{image.id}/")
    assert response.status_code == 200
    assert response["Cache-Control"] == "public, max-age=3600"
    assert response["Content-Disposition"] == "inline"
    storage_open.assert_called_once_with("public/preview.jpg", "rb")

    image.state = ListingImageState.DELETED
    image.save(update_fields=("state",))
    assert client.get(f"/images/{image.id}/").status_code == 404

    public_auto.county.is_network_enabled = False
    public_auto.county.save(update_fields=("is_network_enabled",))
    assert client.get(f"/images/{image.id}/").status_code == 404


def test_public_listing_social_image_uses_processed_rendition_with_stable_layout(
    client: Client, public_auto: Listing
) -> None:
    upload = UploadSession.objects.create(
        listing=public_auto,
        seller=public_auto.seller,
        expires_at=timezone.now() + timedelta(hours=1),
    )
    image = ListingImage.objects.create(
        listing=public_auto,
        upload_session=upload,
        ordering=0,
        state=ListingImageState.READY,
        moderation_status=ListingImageModerationStatus.APPROVED,
        content_type="image/jpeg",
        byte_size=1,
        width=640,
        height=480,
        storage_key="private/original-mustang.jpg",
        rendition_key="public/processed-mustang.jpg",
        original_filename="mustang.jpg",
    )
    public_auto.description = "Private detail text must not become social metadata."
    public_auto.save(update_fields=("description",))

    response = client.get(f"/texas/potter/listing/{public_auto.id}/?campaign=private")

    assert response.status_code == 200
    assert (
        f'<meta property="og:image" content="http://testserver/images/{image.id}/">'.encode()
        in response.content
    )
    assert b'<meta property="og:image:width" content="640">' in response.content
    assert b'<meta property="og:image:height" content="480">' in response.content
    assert b'<meta name="twitter:card" content="summary_large_image">' in response.content
    assert f'src="/images/{image.id}/"'.encode() in response.content
    assert b'alt="Public Mustang image 1"' in response.content
    assert b'width="640" height="480"' in response.content
    assert b"private/original-mustang.jpg" not in response.content
    assert (
        b"Private detail text must not become social metadata."
        not in response.content.split(b"</head>", maxsplit=1)[0]
    )
    browse = client.get("/texas/")
    assert (
        f'<img class="listing-card-image" src="/images/{image.id}/" alt="Public Mustang image" '
        'width="640" height="480" loading="lazy" decoding="async">'.encode()
        in browse.content
    )


@override_settings(DEBUG=True)
def test_nationwide_seed_limit_is_idempotent_and_presents_every_typed_listing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    call_command("seed_marketplace_catalog")
    state = State.objects.create(
        fips="48",
        usps_code="TX",
        name="Texas",
        slug="texas",
        is_active=True,
        is_network_enabled=True,
    )
    first = County.objects.create(
        fips="48001",
        state=state,
        name="Anderson",
        slug="anderson",
        is_active=True,
        is_network_enabled=True,
    )
    County.objects.create(
        fips="48003",
        state=state,
        name="Andrews",
        slug="andrews",
        is_active=True,
        is_network_enabled=True,
    )

    call_command("seed_nationwide_demo_inventory", "--limit-counties", "1")
    first_run = capsys.readouterr().out
    call_command("seed_nationwide_demo_inventory", "--limit-counties", "1")
    second_run = capsys.readouterr().out

    listings = list(
        Listing.objects.filter(county=first, status=ListingStatus.PUBLISHED).select_related(
            "category", "county", "state", "vertical"
        )
    )
    assert len(listings) == 8
    assert Listing.objects.filter(status=ListingStatus.PUBLISHED).count() == 8
    assert "8 created" in first_run
    assert "8 unchanged" in second_run
    for listing in listings:
        presentation = present_public_listing(listing=listing)
        assert presentation.summary
        assert presentation.location == "Anderson, Anderson, TX"

    listings[0].status = ListingStatus.DRAFT
    listings[0].published_at = None
    listings[0].save(update_fields=("status", "published_at"))
    call_command("seed_nationwide_demo_inventory", "--limit-counties", "1")
    assert "0 created, 1 updated, 7 unchanged" in capsys.readouterr().out
    listings[0].refresh_from_db()
    assert listings[0].status == ListingStatus.PUBLISHED


@override_settings(DEBUG=True)
def test_typed_presentations_keep_addresses_opt_in_and_vin_private(client: Client) -> None:
    call_command("seed_marketplace_catalog")
    state = State.objects.create(
        fips="48",
        usps_code="TX",
        name="Texas",
        slug="texas",
        is_active=True,
        is_network_enabled=True,
    )
    county = County.objects.create(
        fips="48001",
        state=state,
        name="Anderson",
        slug="anderson",
        is_active=True,
        is_network_enabled=True,
    )
    call_command("seed_nationwide_demo_inventory", "--limit-counties", "1")
    listings = {
        listing.vertical.slug: listing
        for listing in Listing.objects.filter(county=county)
        .select_related(
            "category",
            "county",
            "state",
            "vertical",
            "auto_details",
            "home_details",
            "rental_details",
        )
        .prefetch_related(
            "ag_equipment_details", "pasture_details", "livestock_details", "home_goods_details"
        )
    }
    home = listings["real-estate"].home_details
    home.street_address = "100 Private Road"
    home.address_line_2 = "Unit 5"
    home.postal_code = "75001"
    home.exact_address_public = False
    home.save()
    private_home_presentation = present_public_listing(listing=listings["real-estate"])
    assert private_home_presentation.address == "General county area"
    assert private_home_presentation.map_query == "Anderson, Anderson, TX"
    assert "Private Road" not in private_home_presentation.map_query
    private_detail_response = client.get(f"/texas/anderson/listing/{listings['real-estate'].id}/")
    assert private_detail_response.status_code == 200
    assert b"100 Private Road" not in private_detail_response.content
    assert b"Unit 5" not in private_detail_response.content
    assert b"75001" not in private_detail_response.content
    assert (
        b"https://www.google.com/maps?q=Anderson%2C%20Anderson%2C%20TX&amp;output=embed"
        in private_detail_response.content
    )
    home.exact_address_public = True
    home.save()
    public_home_presentation = present_public_listing(listing=listings["real-estate"])
    assert public_home_presentation.address == ("100 Private Road, Unit 5, 75001")
    assert public_home_presentation.map_query == (
        "100 Private Road, Unit 5, 75001, Anderson, Anderson, TX"
    )
    detail_response = client.get(f"/texas/anderson/listing/{listings['real-estate'].id}/")
    assert detail_response.status_code == 200
    assert b"100%20Private%20Road%2C%20Unit%205%2C%2075001" in detail_response.content
    assert (
        b"https://www.google.com/maps?q=100%20Private%20Road%2C%20Unit%205%2C%2075001%2C%20Anderson%2C%20Anderson%2C%20TX&amp;output=embed"
        in detail_response.content
    )

    rental = listings["rentals"].rental_details
    rental.street_address = "200 Private Lane"
    rental.exact_address_public = False
    rental.save()
    assert present_public_listing(listing=listings["rentals"]).address == "General county area"
    rental.exact_address_public = True
    rental.save()
    assert present_public_listing(listing=listings["rentals"]).address == "200 Private Lane"
    assert "vin" not in str(present_public_listing(listing=listings["autos"])).lower()


@override_settings(DEBUG=True)
def test_public_broker_attribution_is_an_eligible_listing_fact_only(client: Client) -> None:
    call_command("seed_marketplace_catalog")
    state = State.objects.create(
        fips="48",
        usps_code="TX",
        name="Texas",
        slug="texas",
        is_active=True,
        is_network_enabled=True,
    )
    county = County.objects.create(
        fips="48001",
        state=state,
        name="Anderson",
        slug="anderson",
        is_active=True,
        is_network_enabled=True,
    )
    call_command("seed_nationwide_demo_inventory", "--limit-counties", "1")
    home = Listing.objects.get(county=county, vertical__slug="real-estate")
    home.broker_name = "Piney Woods Realty"
    home.full_clean()
    home.save(update_fields=("broker_name", "updated_at"))

    presentation = present_public_listing(listing=home)
    response = client.get(f"/texas/anderson/listing/{home.id}/")

    assert ("Broker or brokerage", "Piney Woods Realty") in presentation.facts
    assert presentation.map_query == "Anderson, Anderson, TX"
    assert all(
        "Piney Woods Realty" not in terms for terms in public_search_terms(listing=home).values()
    )
    assert response.status_code == 200
    assert b"Broker or brokerage" in response.content
    assert b"Piney Woods Realty" in response.content
    assert b"Piney Woods Realty" not in response.content.split(b"</head>", maxsplit=1)[0]


@override_settings(DEBUG=True)
def test_broker_attribution_edit_is_material_for_published_home() -> None:
    call_command("seed_marketplace_catalog")
    state = State.objects.create(
        fips="48",
        usps_code="TX",
        name="Texas",
        slug="texas",
        is_active=True,
        is_network_enabled=True,
    )
    county = County.objects.create(
        fips="48001",
        state=state,
        name="Anderson",
        slug="anderson",
        is_active=True,
        is_network_enabled=True,
    )
    call_command("seed_nationwide_demo_inventory", "--limit-counties", "1")
    home = Listing.objects.get(county=county, vertical__slug="real-estate")
    details = home.home_details

    updated = update_home_draft(
        listing_id=home.id,
        seller=home.seller,
        listing_values={
            "category": home.category,
            "state": home.state,
            "county": home.county,
            "city": home.city,
            "title": home.title,
            "description": home.description,
            "broker_name": "Piney Woods Realty",
            "price_minor": home.price_minor,
            "currency": home.currency,
        },
        home_values={
            field: getattr(details, field)
            for field in (
                "property_type",
                "beds",
                "baths",
                "square_feet",
                "year_built",
                "lot_size",
                "lot_size_unit",
                "street_address",
                "address_line_2",
                "postal_code",
                "general_area",
                "exact_address_public",
            )
        },
    )

    assert updated.broker_name == "Piney Woods Realty"
    assert updated.status == ListingStatus.IN_REVIEW
    assert updated.published_at is None
    assert not public_listing_with_images().filter(pk=home.pk).exists()


def test_generic_public_form_filters_autos_and_rejects_mismatched_category(
    public_auto: Listing,
) -> None:
    form = PublicBrowseForm(
        {
            "vertical": str(public_auto.vertical_id),
            "category": str(public_auto.category_id),
            "min_price": "20000",
            "max_price": "40000",
            "min_year": "2019",
            "max_year": "2021",
            "make": "Ford",
            "model": "Mustang",
            "min_mileage": "10000",
            "max_mileage": "13000",
            "sort": "year_desc",
        },
        state=public_auto.state,
    )
    assert form.is_valid(), form.errors
    assert list(apply_public_filters(Listing.objects.all(), form)) == [public_auto]

    other_vertical = Vertical.objects.create(name="Other", slug="other")
    other_category = Category.objects.create(vertical=other_vertical, name="Other", slug="other")
    invalid = PublicBrowseForm(
        {"vertical": str(public_auto.vertical_id), "category": str(other_category.id)},
        state=public_auto.state,
    )
    assert not invalid.is_valid()
    assert "category" in invalid.errors


def test_browse_pagination_preserves_filters_and_canonical_omits_query(
    client: Client, public_auto: Listing
) -> None:
    for number in range(25):
        listing = create_auto_draft(
            seller=public_auto.seller,
            listing_values={
                "category": public_auto.category,
                "state": public_auto.state,
                "county": public_auto.county,
                "city": "Amarillo",
                "title": f"Public Mustang {number}",
                "description": "Pagination listing",
                "price_minor": 3_000_000 + number,
                "currency": "USD",
            },
            auto_values={
                "vehicle_type": "car",
                "year": 2020,
                "make": "Ford",
                "model": "Mustang",
                "trim": "",
                "mileage": 12_000 + number,
                "title_status": "clean",
                "vin": "",
            },
        )
        publish_auto_listing(listing_id=listing.id)

    response = client.get("/texas/", {"q": "Mustang", "sort": "price_asc", "page": "2"})
    page_one = client.get("/texas/", {"q": "Mustang", "page": "1"})

    assert response.status_code == 200
    assert b"Page 2 of 2" in response.content
    assert b"?q=Mustang&amp;sort=price_asc&amp;page=1" in response.content
    assert b'<link rel="canonical" href="http://testserver/texas/">' in response.content
    assert page_one.status_code == 200
