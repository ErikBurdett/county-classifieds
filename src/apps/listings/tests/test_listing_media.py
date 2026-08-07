from __future__ import annotations

from datetime import timedelta
from io import BytesIO

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.accounts.models import SellerProfile, User
from apps.catalog.models import Category, ListingKind, Vertical
from apps.listings.models import (
    GenericListingDetails,
    Listing,
    ListingImage,
    ListingImageState,
    ListingIntent,
    ListingMediaPolicy,
    ListingStatus,
    ListingVideo,
    ListingVideoModerationStatus,
    ListingVideoState,
    UploadSessionState,
)
from apps.listings.services import (
    begin_image_upload,
    delete_listing_image,
    finalize_image_upload,
    image_policy_for_listing,
    reorder_images,
    upload_listing_video,
)
from apps.locations.models import County, State

pytestmark = pytest.mark.django_db


@pytest.fixture
def draft() -> tuple[Listing, SellerProfile]:
    user = User.objects.create_user(email="owner@example.com", password="test-password")
    seller = SellerProfile.objects.create(user=user, display_name="Owner")
    vertical = Vertical.objects.create(name="Autos", slug="autos")
    category = Category.objects.create(vertical=vertical, name="Cars", slug="cars")
    state = State.objects.create(fips="48", usps_code="TX", name="Texas", slug="texas")
    county = County.objects.create(fips="48375", state=state, name="Potter", slug="potter")
    return (
        Listing.objects.create(
            seller=seller,
            vertical=vertical,
            category=category,
            state=state,
            county=county,
            city="Amarillo",
            title="Private car",
            description="draft",
            price_minor=100,
            currency="USD",
        ),
        seller,
    )


def image_upload(*, fmt: str = "JPEG", size: tuple[int, int] = (20, 10)) -> SimpleUploadedFile:
    payload = BytesIO()
    Image.new("RGB", size, "red").save(payload, format=fmt)
    return SimpleUploadedFile(f"hostile.<{fmt}>", payload.getvalue(), content_type="text/plain")


def upload_image(listing: Listing, seller: SellerProfile) -> ListingImage:
    session = begin_image_upload(
        listing_id=listing.id,
        seller=seller,
        original_filename="hostile-name.jpg",
    )
    return finalize_image_upload(session_id=session.id, seller=seller, uploaded_file=image_upload())


def video_upload(*, content: bytes | None = None) -> SimpleUploadedFile:
    return SimpleUploadedFile(
        "hostile.<mp4>",
        content or b"\x00\x00\x00\x18ftypisom" + b"\x00" * 32,
        content_type="text/plain",
    )


def test_finalized_image_is_reencoded_without_exif(draft: tuple[Listing, SellerProfile]) -> None:
    listing, seller = draft
    image = upload_image(listing, seller)

    assert image.content_type == "image/jpeg"
    assert image.original_filename == "hostile-name.jpg"
    assert image.width == 20
    assert image.upload_session.state == UploadSessionState.FINALIZED


def test_upload_locks_only_non_nullable_listing_relations(
    draft: tuple[Listing, SellerProfile],
) -> None:
    """A nullable listing kind must not be joined into a FOR UPDATE query.

    SQLite exercises the normal path; PostgreSQL exercises the locking regression.
    """
    listing, seller = draft

    session = begin_image_upload(
        listing_id=listing.id,
        seller=seller,
        original_filename="postgresql-safe.jpg",
    )
    image = finalize_image_upload(
        session_id=session.id,
        seller=seller,
        uploaded_file=image_upload(),
    )

    assert image.listing_id == listing.id


def test_wanted_listing_uses_the_shared_media_workflow(
    draft: tuple[Listing, SellerProfile],
) -> None:
    listing, seller = draft
    listing.intent = ListingIntent.WANTED
    listing.listing_kind = None
    listing.save(update_fields=("intent", "listing_kind"))
    GenericListingDetails.objects.create(listing=listing, price_mode="contact", postal_code="79101")

    image = upload_image(listing, seller)

    assert image.listing_id == listing.id
    assert image.state == ListingImageState.READY


def test_rejects_corrupt_wrong_type_and_dimension_guards(
    draft: tuple[Listing, SellerProfile], monkeypatch: pytest.MonkeyPatch
) -> None:
    listing, seller = draft
    session = begin_image_upload(listing_id=listing.id, seller=seller, original_filename="bad.jpg")
    with pytest.raises(ValidationError, match="valid"):
        finalize_image_upload(
            session_id=session.id,
            seller=seller,
            uploaded_file=SimpleUploadedFile("bad.jpg", b"not-an-image"),
        )
    monkeypatch.setattr("apps.listings.services.MAX_IMAGE_DIMENSION", 10)
    session = begin_image_upload(
        listing_id=listing.id, seller=seller, original_filename="large.jpg"
    )
    with pytest.raises(ValidationError, match="dimensions"):
        finalize_image_upload(
            session_id=session.id, seller=seller, uploaded_file=image_upload(size=(20, 20))
        )


def test_policy_defaults_to_no_minimum_and_category_overrides(
    draft: tuple[Listing, SellerProfile],
) -> None:
    listing, _seller = draft
    assert image_policy_for_listing(listing=listing)[0] == 0
    ListingMediaPolicy.objects.create(
        category=listing.category,
        required_image_count=2,
        maximum_image_count=3,
    )
    assert image_policy_for_listing(listing=listing) == (2, 3)


def test_policy_can_target_listing_kind(draft: tuple[Listing, SellerProfile]) -> None:
    listing, _seller = draft
    kind = ListingKind.objects.create(vertical=listing.vertical, name="Automobile")
    listing.listing_kind = kind
    listing.save(update_fields=("listing_kind",))
    ListingMediaPolicy.objects.create(listing_kind=kind, maximum_image_count=4)
    assert image_policy_for_listing(listing=listing) == (0, 4)


def test_reorder_delete_and_limit(draft: tuple[Listing, SellerProfile]) -> None:
    listing, seller = draft
    ListingMediaPolicy.objects.create(category=listing.category, maximum_image_count=2)
    first = upload_image(listing, seller)
    second = upload_image(listing, seller)
    reorder_images(listing_id=listing.id, seller=seller, image_ids=[second.id, first.id])
    assert list(ListingImage.objects.values_list("id", flat=True).order_by("ordering")) == [
        second.id,
        first.id,
    ]
    with pytest.raises(ValidationError, match="limit"):
        begin_image_upload(listing_id=listing.id, seller=seller, original_filename="third.jpg")
    delete_listing_image(listing_id=listing.id, image_id=second.id, seller=seller)
    assert ListingImage.objects.get(pk=first.id).ordering == 0


def test_non_owner_cannot_change_or_read_private_media(
    draft: tuple[Listing, SellerProfile],
) -> None:
    listing, seller = draft
    image = upload_image(listing, seller)
    other_user = User.objects.create_user(email="other@example.com", password="test-password")
    other = SellerProfile.objects.create(user=other_user, display_name="Other")
    with pytest.raises(PermissionDenied):
        delete_listing_image(listing_id=listing.id, image_id=image.id, seller=other)
    client = Client()
    client.force_login(other_user)
    response = client.get(
        reverse(
            "listings:private_listing_image",
            kwargs={"listing_id": listing.id, "image_id": image.id, "rendition": "preview"},
        )
    )
    assert response.status_code == 404


def test_upload_mutation_requires_csrf_and_owner_can_preview(
    draft: tuple[Listing, SellerProfile],
) -> None:
    listing, seller = draft
    client = Client(enforce_csrf_checks=True)
    client.force_login(seller.user)
    upload_url = reverse("listings:upload_listing_image", kwargs={"listing_id": listing.id})
    assert client.post(upload_url, {"image": image_upload()}).status_code == 403

    image = upload_image(listing, seller)
    response = client.get(
        reverse(
            "listings:private_listing_image",
            kwargs={"listing_id": listing.id, "image_id": image.id, "rendition": "preview"},
        )
    )
    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    assert response["X-Robots-Tag"].startswith("noindex")


def test_cleanup_command_is_idempotent() -> None:
    call_command("cleanup_listing_media")
    call_command("cleanup_listing_media")


def test_owner_media_routes_upload_reorder_and_delete(
    draft: tuple[Listing, SellerProfile],
) -> None:
    listing, seller = draft
    client = Client()
    client.force_login(seller.user)
    manage_url = reverse("listings:media_manage", kwargs={"listing_id": listing.id})
    upload_url = reverse("listings:upload_listing_image", kwargs={"listing_id": listing.id})

    assert client.get(manage_url).status_code == 200
    assert client.get(upload_url).status_code == 405
    assert client.post(upload_url, {"image": image_upload()}).status_code == 302
    assert client.post(upload_url, {"image": image_upload()}).status_code == 302
    first, second = ListingImage.objects.filter(state=ListingImageState.READY).order_by("ordering")

    reorder_url = reverse("listings:reorder_listing_images", kwargs={"listing_id": listing.id})
    response = client.post(
        reorder_url,
        {"image_id": [str(first.id), str(second.id)], "order": ["2", "1"]},
    )
    assert response.status_code == 302
    assert list(
        ListingImage.objects.filter(state=ListingImageState.READY).values_list("id", flat=True)
    ) == [second.id, first.id]

    delete_url = reverse(
        "listings:delete_listing_image",
        kwargs={"listing_id": listing.id, "image_id": second.id},
    )
    assert client.post(delete_url).status_code == 302
    assert ListingImage.objects.get(pk=second.id).state == ListingImageState.DELETED


def test_media_rejects_disabled_expired_and_invalid_requests(
    draft: tuple[Listing, SellerProfile],
) -> None:
    listing, seller = draft
    with (
        override_settings(LISTING_MEDIA_ENABLED=False),
        pytest.raises(ValidationError, match="configured"),
    ):
        begin_image_upload(listing_id=listing.id, seller=seller, original_filename="image.jpg")

    session = begin_image_upload(
        listing_id=listing.id, seller=seller, original_filename="image.jpg"
    )
    session.expires_at = timezone.now() - timedelta(seconds=1)
    session.save(update_fields=("expires_at",))
    with pytest.raises(ValidationError, match="expired"):
        finalize_image_upload(session_id=session.id, seller=seller, uploaded_file=image_upload())
    session.refresh_from_db()
    assert session.state == UploadSessionState.EXPIRED

    client = Client()
    client.force_login(seller.user)
    upload_url = reverse("listings:upload_listing_image", kwargs={"listing_id": listing.id})
    assert client.post(upload_url).status_code == 302
    image = upload_image(listing, seller)
    private_url = reverse(
        "listings:private_listing_image",
        kwargs={"listing_id": listing.id, "image_id": image.id, "rendition": "unexpected"},
    )
    assert client.get(private_url).status_code == 404
    reorder_url = reverse("listings:reorder_listing_images", kwargs={"listing_id": listing.id})
    assert client.post(reorder_url, {"image_id": str(image.id), "order": "2"}).status_code == 302


def test_video_upload_validates_signature_size_and_published_rereview(
    draft: tuple[Listing, SellerProfile], monkeypatch: pytest.MonkeyPatch
) -> None:
    listing, seller = draft
    with pytest.raises(ValidationError, match="MP4"):
        upload_listing_video(
            listing_id=listing.id,
            seller=seller,
            uploaded_file=video_upload(content=b"not a video"),
        )
    monkeypatch.setattr("apps.listings.services.MAX_VIDEO_BYTES", 10)
    with pytest.raises(ValidationError, match="100 MB"):
        upload_listing_video(
            listing_id=listing.id,
            seller=seller,
            uploaded_file=video_upload(),
        )
    monkeypatch.setattr("apps.listings.services.MAX_VIDEO_BYTES", 100 * 1024 * 1024)
    listing.status = ListingStatus.PUBLISHED
    listing.published_at = timezone.now()
    listing.save(update_fields=("status", "published_at"))

    video = upload_listing_video(
        listing_id=listing.id,
        seller=seller,
        uploaded_file=video_upload(),
    )
    listing.refresh_from_db()

    assert video.content_type == "video/mp4"
    assert video.state == ListingVideoState.READY
    assert listing.status == ListingStatus.IN_REVIEW


def test_webm_video_upload_is_accepted(draft: tuple[Listing, SellerProfile]) -> None:
    listing, seller = draft

    video = upload_listing_video(
        listing_id=listing.id,
        seller=seller,
        uploaded_file=video_upload(content=b"\x1aE\xdf\xa3webm" + b"\x00" * 16),
    )

    assert video.content_type == "video/webm"


def test_video_private_routes_require_owner_and_support_delete(
    draft: tuple[Listing, SellerProfile],
) -> None:
    listing, seller = draft
    video = upload_listing_video(
        listing_id=listing.id,
        seller=seller,
        uploaded_file=video_upload(),
    )
    other_user = User.objects.create_user(email="video-other@example.com", password="test-password")
    SellerProfile.objects.create(user=other_user, display_name="Video Other")
    client = Client()
    client.force_login(other_user)
    private_url = reverse(
        "listings:private_listing_video",
        kwargs={"listing_id": listing.id, "video_id": video.id},
    )
    assert client.get(private_url).status_code == 404
    client.force_login(seller.user)
    assert client.get(private_url).status_code == 200
    delete_url = reverse(
        "listings:delete_listing_video",
        kwargs={"listing_id": listing.id, "video_id": video.id},
    )
    assert client.post(delete_url).status_code == 302
    assert ListingVideo.objects.get(pk=video.id).state == ListingVideoState.DELETED


def test_public_video_delivery_requires_individual_approval(
    draft: tuple[Listing, SellerProfile],
) -> None:
    listing, _seller = draft
    listing.state.is_active = True
    listing.state.is_network_enabled = True
    listing.state.save(update_fields=("is_active", "is_network_enabled"))
    listing.county.is_active = True
    listing.county.is_network_enabled = True
    listing.county.save(update_fields=("is_active", "is_network_enabled"))
    listing.status = ListingStatus.PUBLISHED
    listing.published_at = timezone.now()
    listing.save(update_fields=("status", "published_at"))
    storage_key = f"private-listings/{listing.id}/public-video.mp4"
    default_storage.save(storage_key, ContentFile(b"\x00\x00\x00\x18ftypisom"))
    video = ListingVideo.objects.create(
        listing=listing,
        content_type="video/mp4",
        byte_size=12,
        storage_key=storage_key,
        original_filename="public.mp4",
    )
    client = Client()
    url = reverse("locations:public_listing_video", kwargs={"video_id": video.id})

    assert client.get(url).status_code == 404
    video.moderation_status = ListingVideoModerationStatus.APPROVED
    video.save(update_fields=("moderation_status",))
    assert client.get(url).status_code == 200
