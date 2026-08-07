from __future__ import annotations

from uuid import UUID

from django.db.models import ExpressionWrapper, FloatField, Prefetch, Q, QuerySet, Value
from django.db.models.functions import ACos, Cos, Greatest, Least, Radians, Sin
from django.http import Http404
from django.utils import timezone

from apps.accounts.models import AccountStatus, SellerProfile, User
from apps.locations.models import County

from .models import (
    Listing,
    ListingImage,
    ListingImageModerationStatus,
    ListingImageState,
    ListingStatus,
    ListingVideo,
    ListingVideoModerationStatus,
    ListingVideoState,
)


def get_owned_draft(*, listing_id: UUID, seller: SellerProfile) -> Listing:
    try:
        return (
            Listing.objects.select_related(
                "category",
                "county",
                "seller",
                "state",
                "vertical",
                "auto_details",
                "ag_equipment_details",
                "home_details",
                "home_goods_details",
                "livestock_details",
                "pasture_details",
                "rental_details",
                "generic_details",
            )
            .filter(pk=listing_id, seller=seller, status=ListingStatus.DRAFT)
            .get()
        )
    except Listing.DoesNotExist as error:
        raise Http404("Draft not found.") from error


def get_seller_drafts(*, seller: SellerProfile) -> QuerySet[Listing]:
    return (
        Listing.objects.filter(seller=seller, status=ListingStatus.DRAFT)
        .select_related("category", "county", "state", "vertical")
        .order_by("-updated_at")
    )


def get_seller_listings(*, seller: SellerProfile) -> QuerySet[Listing]:
    return (
        Listing.objects.filter(seller=seller)
        .select_related("category", "county", "state", "vertical", "assigned_moderator")
        .prefetch_related(
            "moderation_actions__reason_code",
            "controlled_tags__category",
            "seller_tags",
            "custom_fields",
        )
        .order_by("-updated_at")
    )


def get_user_favorites(*, user: User) -> QuerySet[Listing]:
    """Return only currently public rows, so old bookmarks disclose nothing private."""
    return public_listings().filter(favorites__user=user).order_by("-favorites__created_at")


def get_owned_listing(*, listing_id: UUID, seller: SellerProfile) -> Listing:
    try:
        return (
            Listing.objects.select_related(
                "category",
                "county",
                "seller",
                "state",
                "vertical",
                "auto_details",
                "ag_equipment_details",
                "home_details",
                "home_goods_details",
                "livestock_details",
                "pasture_details",
                "rental_details",
                "generic_details",
            )
            .prefetch_related(
                "moderation_actions__reason_code",
                "controlled_tags__category",
                "seller_tags",
                "custom_fields",
            )
            .get(pk=listing_id, seller=seller)
        )
    except Listing.DoesNotExist as error:
        raise Http404("Listing not found.") from error


def moderation_queue() -> QuerySet[Listing]:
    return (
        Listing.objects.filter(status=ListingStatus.IN_REVIEW)
        .select_related(
            "seller__user", "vertical", "category", "state", "county", "assigned_moderator"
        )
        .prefetch_related(
            "controlled_tags__category", "seller_tags", "custom_fields", "images", "videos"
        )
        .order_by("created_at")
    )


def get_owned_home_draft(*, listing_id: UUID, seller: SellerProfile) -> Listing:
    try:
        return Listing.objects.select_related(
            "category", "county", "seller", "state", "vertical", "home_details"
        ).get(
            pk=listing_id,
            seller=seller,
            status=ListingStatus.DRAFT,
            vertical__slug="real-estate",
        )
    except Listing.DoesNotExist as error:
        raise Http404("Home draft not found.") from error


def get_owned_rental_draft(*, listing_id: UUID, seller: SellerProfile) -> Listing:
    try:
        return Listing.objects.select_related(
            "category", "county", "seller", "state", "vertical", "rental_details"
        ).get(
            pk=listing_id,
            seller=seller,
            status=ListingStatus.DRAFT,
            vertical__slug="rentals",
        )
    except Listing.DoesNotExist as error:
        raise Http404("Rental draft not found.") from error


def get_owned_ag_equipment_draft(*, listing_id: UUID, seller: SellerProfile) -> Listing:
    try:
        return Listing.objects.select_related(
            "category", "county", "seller", "state", "vertical", "ag_equipment_details"
        ).get(
            pk=listing_id,
            seller=seller,
            status=ListingStatus.DRAFT,
            vertical__slug="farm-ranch",
        )
    except Listing.DoesNotExist as error:
        raise Http404("Agricultural equipment draft not found.") from error


def get_owned_livestock_draft(*, listing_id: UUID, seller: SellerProfile) -> Listing:
    try:
        return Listing.objects.select_related(
            "category", "county", "seller", "state", "vertical", "livestock_details"
        ).get(
            pk=listing_id,
            seller=seller,
            status=ListingStatus.DRAFT,
            vertical__slug="livestock-animals",
        )
    except Listing.DoesNotExist as error:
        raise Http404("Livestock draft not found.") from error


def get_owned_pasture_draft(*, listing_id: UUID, seller: SellerProfile) -> Listing:
    try:
        return Listing.objects.select_related(
            "category", "county", "seller", "state", "vertical", "pasture_details"
        ).get(
            pk=listing_id,
            seller=seller,
            status=ListingStatus.DRAFT,
            vertical__slug="farm-ranch",
        )
    except Listing.DoesNotExist as error:
        raise Http404("Pasture draft not found.") from error


def get_owned_home_garden_draft(*, listing_id: UUID, seller: SellerProfile) -> Listing:
    try:
        return Listing.objects.select_related(
            "category", "county", "seller", "state", "vertical", "home_goods_details"
        ).get(
            pk=listing_id,
            seller=seller,
            status=ListingStatus.DRAFT,
            vertical__slug="home-garden",
        )
    except Listing.DoesNotExist as error:
        raise Http404("Home & Garden draft not found.") from error


def get_owned_appliances_draft(*, listing_id: UUID, seller: SellerProfile) -> Listing:
    try:
        return Listing.objects.select_related(
            "category", "county", "seller", "state", "vertical", "home_goods_details"
        ).get(
            pk=listing_id,
            seller=seller,
            status=ListingStatus.DRAFT,
            vertical__slug="appliances",
        )
    except Listing.DoesNotExist as error:
        raise Http404("Appliances draft not found.") from error


def public_listings() -> QuerySet[Listing]:
    """The sole visibility boundary for every buyer-facing listing surface."""
    return (
        Listing.objects.filter(
            status=ListingStatus.PUBLISHED,
            vertical__is_active=True,
            category__is_active=True,
            state__is_active=True,
            state__is_network_enabled=True,
            county__is_active=True,
            county__is_network_enabled=True,
        )
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
        .select_related(
            "category",
            "county",
            "seller",
            "state",
            "vertical",
            "auto_details",
            "ag_equipment_details",
            "home_details",
            "home_goods_details",
            "livestock_details",
            "pasture_details",
            "rental_details",
            "generic_details",
        )
        .prefetch_related("controlled_tags__category", "seller_tags", "custom_fields")
        .defer("auto_details__vin")
    )


def public_seller_feed_listings(*, seller: SellerProfile) -> QuerySet[Listing]:
    """Return a seller's active listings and recently sold, still-public listings."""
    now = timezone.now()
    return (
        Listing.objects.filter(
            seller=seller,
            seller__user__account_status=AccountStatus.ACTIVE,
            seller__user__is_active=True,
            vertical__is_active=True,
            category__is_active=True,
            state__is_active=True,
            state__is_network_enabled=True,
            county__is_active=True,
            county__is_network_enabled=True,
        )
        .filter(
            Q(
                status=ListingStatus.PUBLISHED,
                expires_at__isnull=True,
            )
            | Q(
                status=ListingStatus.PUBLISHED,
                expires_at__gt=now,
            )
            | Q(
                status=ListingStatus.SOLD,
                sold_at__isnull=False,
                sold_public_until__gt=now,
            )
        )
        .select_related(
            "seller",
            "seller__user",
            "category",
            "county",
            "state",
            "vertical",
            "auto_details",
            "ag_equipment_details",
            "home_details",
            "home_goods_details",
            "livestock_details",
            "pasture_details",
            "rental_details",
            "generic_details",
        )
        .prefetch_related(
            "controlled_tags__category",
            "seller_tags",
            "custom_fields",
            Prefetch(
                "images",
                queryset=ListingImage.objects.filter(
                    state=ListingImageState.READY,
                    moderation_status=ListingImageModerationStatus.APPROVED,
                ).only(
                    "id",
                    "listing_id",
                    "ordering",
                    "content_type",
                    "rendition_key",
                    "width",
                    "height",
                ),
            ),
        )
        .defer("auto_details__vin")
        .order_by("-first_published_at", "-published_at", "-id")
    )


NEARBY_LISTING_LIMIT = 12
EARTH_RADIUS_MILES = 3958.7613
NEARBY_RADIUS_MIN_MILES = 10
NEARBY_RADIUS_MAX_MILES = 250
NEARBY_RADIUS_STEP_MILES = 10


def public_listings_near_county(
    *, county: County, radius_miles: int, limit: int = NEARBY_LISTING_LIMIT
) -> QuerySet[Listing]:
    """Return public listings ordered by approximate Census county-point distance."""
    if (
        county.centroid_latitude is None
        or county.centroid_longitude is None
        or radius_miles < NEARBY_RADIUS_MIN_MILES
        or radius_miles > NEARBY_RADIUS_MAX_MILES
        or radius_miles % NEARBY_RADIUS_STEP_MILES
        or limit < 1
    ):
        return Listing.objects.none()

    latitude_radians = Radians(Value(float(county.centroid_latitude)))
    longitude_radians = Radians(Value(float(county.centroid_longitude)))
    target_latitude = Radians("county__centroid_latitude")
    target_longitude = Radians("county__centroid_longitude")
    cosine_distance = Sin(latitude_radians) * Sin(target_latitude) + Cos(latitude_radians) * Cos(
        target_latitude
    ) * Cos(target_longitude - longitude_radians)
    distance = ExpressionWrapper(
        Value(EARTH_RADIUS_MILES) * ACos(Least(Value(1.0), Greatest(Value(-1.0), cosine_distance))),
        output_field=FloatField(),
    )
    return (
        public_listings()
        .exclude(county=county)
        .filter(
            county__centroid_latitude__isnull=False,
            county__centroid_longitude__isnull=False,
        )
        .annotate(nearby_distance_miles=distance)
        .filter(nearby_distance_miles__lte=radius_miles)
        .order_by("nearby_distance_miles", "-published_at", "-id")[:limit]
    )


def public_listing_with_images() -> QuerySet[Listing]:
    """Public listing selector with processed, ready image records only."""
    return public_listings().prefetch_related(
        Prefetch(
            "images",
            queryset=ListingImage.objects.filter(
                state=ListingImageState.READY,
                moderation_status=ListingImageModerationStatus.APPROVED,
            ).only(
                "id",
                "listing_id",
                "ordering",
                "content_type",
                "rendition_key",
                "width",
                "height",
            ),
        )
    )


def public_listing_with_media() -> QuerySet[Listing]:
    """Public detail selector with approved images and supplemental videos only."""
    return public_listing_with_images().prefetch_related(
        Prefetch(
            "videos",
            queryset=ListingVideo.objects.filter(
                state=ListingVideoState.READY,
                moderation_status=ListingVideoModerationStatus.APPROVED,
            ).only("id", "listing_id", "content_type", "byte_size"),
        )
    )


def public_listing_for_location(*, listing_id: UUID, state_slug: str, county_slug: str) -> Listing:
    """Resolve a canonical public listing without revealing non-public records."""
    try:
        return (
            public_listing_with_media()
            .filter(pk=listing_id, state__slug=state_slug)
            .filter(Q(county__slug=county_slug) | Q(additional_counties__county__slug=county_slug))
            .distinct()
            .get()
        )
    except Listing.DoesNotExist as error:
        raise Http404("Listing not found.") from error


def public_autos_for_state(*, state_slug: str) -> QuerySet[Listing]:
    return public_autos_listings().filter(state__slug=state_slug)


def public_autos_for_county(*, state_slug: str, county_slug: str) -> QuerySet[Listing]:
    return public_autos_for_state(state_slug=state_slug).filter(county__slug=county_slug)


def public_autos_listings() -> QuerySet[Listing]:
    """Compatibility selector for the established public Autos API."""
    return public_listings().filter(vertical__slug="autos")
