from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import SellerProfile, User
from apps.billing.services import create_checkout_order, record_local_payment
from apps.catalog.models import (
    Category,
    ListingPriceMode,
    ListingProduct,
    ListingProductUseCase,
    ProductPrice,
    Vertical,
)
from apps.listings.models import (
    GenericListingDetails,
    Listing,
    ListingCountyPlacement,
    ListingImage,
    ListingImageModerationStatus,
    ListingImageState,
    ListingMediaPolicy,
    ListingStatus,
    ModerationActionType,
    ModerationReasonCode,
    UploadSession,
)
from apps.listings.selectors import public_listing_with_images
from apps.listings.services import moderate_listing
from apps.locations.models import County, State

pytestmark = pytest.mark.django_db


@pytest.fixture
def review_listing() -> tuple[Listing, User, County]:
    seller_user = User.objects.create_user(email="seller@example.com", password="password")
    seller = SellerProfile.objects.create(user=seller_user, display_name="Seller")
    moderator = User.objects.create_user(email="moderator@example.com", password="password")
    moderator.user_permissions.add(
        Permission.objects.get(content_type__app_label="listings", codename="moderate_listing")
    )
    vertical = Vertical.objects.create(name="Services", slug="services")
    category = Category.objects.create(vertical=vertical, name="Cleaning", slug="cleaning")
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
    listing = Listing.objects.create(
        seller=seller,
        vertical=vertical,
        category=category,
        state=state,
        county=county,
        city="Amarillo",
        title="Approved cleaning",
        description="Local service.",
        status=ListingStatus.IN_REVIEW,
    )
    GenericListingDetails.objects.create(listing=listing, price_mode="contact", postal_code="79101")
    return listing, moderator, county


def test_moderator_can_publish_without_payment(
    review_listing: tuple[Listing, User, County],
) -> None:
    listing, moderator, _county = review_listing

    moderated = moderate_listing(
        listing_id=listing.id,
        actor=moderator,
        revision=listing.lifecycle_revision,
        outcome=ModerationActionType.APPROVED_NO_PAYMENT,
    )

    assert moderated.status == ListingStatus.PUBLISHED
    assert moderated.published_at is not None


@override_settings(DEBUG=True)
def test_moderator_payment_link_prices_all_listing_types_by_county(
    review_listing: tuple[Listing, User, County],
) -> None:
    listing, moderator, county = review_listing
    additional = County.objects.create(
        fips="48113",
        state=county.state,
        name="Dallas",
        slug="dallas",
        is_active=True,
        is_network_enabled=True,
    )
    ListingCountyPlacement.objects.create(listing=listing, county=additional)
    for code, amount in (("GENERIC_PRIMARY_PLACEMENT", 1000), ("GENERIC_ADDITIONAL_COUNTY", 500)):
        product = ListingProduct.objects.create(
            product_code=code,
            use_case=ListingProductUseCase.NEW_LISTING,
            price_mode=ListingPriceMode.FIXED,
            is_generic_distribution=True,
            duration_days=30,
        )
        ProductPrice.objects.create(
            product=product, currency="USD", amount_minor=amount, effective_from=timezone.now()
        )

    moderated = moderate_listing(
        listing_id=listing.id,
        actor=moderator,
        revision=listing.lifecycle_revision,
        outcome=ModerationActionType.APPROVED_SEND_PAYMENT_LINK,
    )
    order = listing.orders.get()
    assert (
        create_checkout_order(listing_id=listing.id, seller_id=listing.seller_id).order.id
        == order.id
    )
    record_local_payment(order_id=order.id)
    listing.refresh_from_db()

    assert moderated.status == ListingStatus.AWAITING_PAYMENT
    assert order.total_minor == 1500
    assert listing.status == ListingStatus.PUBLISHED


def test_pending_images_need_decisions_and_rejections_gate_required_count(
    review_listing: tuple[Listing, User, County],
) -> None:
    listing, moderator, _county = review_listing
    ListingMediaPolicy.objects.create(category=listing.category, required_image_count=1)
    session = UploadSession.objects.create(
        listing=listing,
        seller=listing.seller,
        expires_at=timezone.now() + timedelta(minutes=30),
    )
    image = ListingImage.objects.create(
        listing=listing,
        upload_session=session,
        ordering=0,
        state=ListingImageState.READY,
        content_type="image/jpeg",
        byte_size=1,
        width=1,
        height=1,
        storage_key="private/test-image.jpg",
        rendition_key="private/test-image-preview.jpg",
        original_filename="test.jpg",
    )

    with pytest.raises(ValidationError, match="Every pending image"):
        moderate_listing(
            listing_id=listing.id,
            actor=moderator,
            revision=listing.lifecycle_revision,
            outcome=ModerationActionType.APPROVED_NO_PAYMENT,
        )

    moderated = moderate_listing(
        listing_id=listing.id,
        actor=moderator,
        revision=listing.lifecycle_revision,
        outcome=ModerationActionType.APPROVED_NO_PAYMENT,
        reason_code=ModerationReasonCode.objects.create(
            code="image_required", category="Images", seller_facing_text="Add a valid image."
        ),
        image_decisions={image.id: (ListingImageModerationStatus.REJECTED, "Image is too blurry.")},
    )
    image.refresh_from_db()

    assert moderated.status == ListingStatus.CHANGES_REQUESTED
    assert image.moderation_status == ListingImageModerationStatus.REJECTED
    assert image.moderation_reason == "Image is too blurry."
    assert not public_listing_with_images().filter(pk=listing.id).exists()
