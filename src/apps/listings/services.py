from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, cast
from uuid import UUID

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import models, transaction
from django.db.models import Max
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError

from apps.accounts.models import SellerProfile, User
from apps.accounts.services import require_active_account
from apps.billing.models import OrderStatus
from apps.billing.services import create_checkout_order, refund_rejected_listing
from apps.catalog.models import ListingKind, ListingProduct, Vertical
from apps.core.models import OutboxEvent
from apps.core.outbox import enqueue_event
from apps.locations.zip_county import zip_county_candidates
from apps.policies.services import (
    accept_current_listing_policies,
    require_current_listing_acceptances,
)

from .models import (
    MAX_CUSTOM_FIELDS,
    MAX_SELLER_TAGS,
    AgEquipmentDetails,
    AutoDetails,
    Favorite,
    GenericListingDetails,
    HomeDetails,
    HomeGoodsDetails,
    Listing,
    ListingCategoryTag,
    ListingCountyPlacement,
    ListingCustomField,
    ListingImage,
    ListingImageModerationStatus,
    ListingImageState,
    ListingIntent,
    ListingMediaPolicy,
    ListingSellerTag,
    ListingStatus,
    ListingVideo,
    ListingVideoModerationStatus,
    ListingVideoState,
    LivestockDetails,
    ModerationAction,
    ModerationActionType,
    ModerationReasonCode,
    PastureDetails,
    RentalDetails,
    UploadSession,
    UploadSessionState,
)
from .search import rebuild_public_search_document
from .selectors import public_listings
from .workflows import ListingWorkflow, resolve_listing_workflow

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_VIDEO_BYTES = 100 * 1024 * 1024
MAX_IMAGE_DIMENSION = 10_000
UPLOAD_SESSION_LIFETIME_SECONDS = 30 * 60
DEFAULT_MAXIMUM_IMAGE_COUNT = 12
ALLOWED_IMAGE_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
ALLOWED_VIDEO_CONTENT_TYPES = {"video/mp4", "video/webm"}
MP4_SIGNATURE_MINIMUM_BYTES = 12
WEBM_SIGNATURE_MINIMUM_BYTES = 8
VIDEO_SIGNATURE_SCAN_BYTES = 4096
OWNER_EDITABLE_STATUSES = {
    ListingStatus.DRAFT,
    ListingStatus.CHANGES_REQUESTED,
    ListingStatus.PUBLISHED,
}
POLICY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "prohibited_weapons": ("firearm", "gun", "rifle", "pistol", "weapon"),
    "prohibited_controlled_substances": ("cocaine", "heroin", "methamphetamine", "fentanyl"),
    "prohibited_adult_services": ("escort service", "adult services"),
    "prohibited_financial_crypto": ("crypto investment", "guaranteed return", "wire transfer"),
    "prohibited_scams": ("western union", "gift card payment"),
    "prohibited_stolen_counterfeit": ("stolen goods", "counterfeit"),
    "prohibited_trafficking": ("human trafficking",),
}


def _autos_vertical() -> Vertical:
    return Vertical.objects.get(slug="autos", is_active=True)


def _autos_listing_kind() -> ListingKind | None:
    return ListingKind.objects.filter(vertical__slug="autos", is_active=True).order_by("pk").first()


def _homes_vertical() -> Vertical:
    return Vertical.objects.get(slug="real-estate", is_active=True)


def _rentals_vertical() -> Vertical:
    return Vertical.objects.get(slug="rentals", is_active=True)


def _farm_ranch_vertical() -> Vertical:
    return Vertical.objects.get(slug="farm-ranch", is_active=True)


def _livestock_vertical() -> Vertical:
    return Vertical.objects.get(slug="livestock-animals", is_active=True)


def _home_garden_vertical() -> Vertical:
    return Vertical.objects.get(slug="home-garden", is_active=True)


def _appliances_vertical() -> Vertical:
    return Vertical.objects.get(slug="appliances", is_active=True)


def _apply_listing_values(listing: Listing, values: dict[str, Any]) -> None:
    for field_name, value in values.items():
        setattr(listing, field_name, value)


def _mark_published(*, listing: Listing, published_at: datetime) -> None:
    """Set the current publication and preserve the listing's initial publication."""
    listing.published_at = published_at
    if listing.first_published_at is None:
        listing.first_published_at = published_at


def _replace_listing_taxonomy_and_facts(
    *,
    listing: Listing,
    controlled_categories: list[Any],
    seller_tags: list[str],
    custom_fields: list[dict[str, str]],
) -> None:
    """Persist bounded taxonomy/facts after the primary category resolves the workflow."""
    categories = [listing.category, *controlled_categories]
    category_ids = {category.id for category in categories}
    if len(category_ids) != len(categories):
        raise ValidationError("Controlled subcategories must be unique.")
    if any(category.vertical_id != listing.vertical_id for category in categories):
        raise ValidationError("Controlled subcategories must use the listing vertical.")
    controlled_names = {category.name.casefold() for category in categories}
    if len(seller_tags) > MAX_SELLER_TAGS or len(custom_fields) > MAX_CUSTOM_FIELDS:
        raise ValidationError("Too many seller tags or additional details.")
    if any(tag.casefold() in controlled_names for tag in seller_tags):
        raise ValidationError("Seller tags cannot duplicate controlled subcategories.")
    ListingCategoryTag.objects.filter(listing=listing).delete()
    ListingSellerTag.objects.filter(listing=listing).delete()
    ListingCustomField.objects.filter(listing=listing).delete()
    controlled_rows = [
        ListingCategoryTag(listing=listing, category=category) for category in categories
    ]
    for controlled_row in controlled_rows:
        controlled_row.full_clean()
    ListingCategoryTag.objects.bulk_create(controlled_rows)
    tag_rows = [ListingSellerTag(listing=listing, value=value) for value in seller_tags]
    for seller_tag_row in tag_rows:
        seller_tag_row.full_clean()
    ListingSellerTag.objects.bulk_create(tag_rows)
    field_rows = [
        ListingCustomField(listing=listing, label=field["label"], value=field["value"])
        for field in custom_fields
    ]
    for custom_field_row in field_rows:
        custom_field_row.full_clean()
    ListingCustomField.objects.bulk_create(field_rows)


@transaction.atomic
def replace_listing_taxonomy_and_facts(
    *,
    listing_id: UUID,
    seller: SellerProfile,
    controlled_categories: list[Any],
    seller_tags: list[str],
    custom_fields: list[dict[str, str]],
) -> Listing:
    """Replace material seller taxonomy/facts under the owner lock."""
    require_active_account(user=seller.user)
    listing = (
        Listing.objects.select_for_update()
        .select_related("category", "vertical")
        .get(pk=listing_id)
    )
    if listing.seller_id != seller.id:
        raise PermissionDenied("Only the listing owner may edit this listing.")
    if listing.status not in OWNER_EDITABLE_STATUSES:
        raise PermissionDenied("Only draft, changed, or published listings may be edited.")
    previous = listing.status
    _replace_listing_taxonomy_and_facts(
        listing=listing,
        controlled_categories=controlled_categories,
        seller_tags=seller_tags,
        custom_fields=custom_fields,
    )
    _depublish_material_edit(listing=listing, seller=seller, previous=previous)
    return listing


def _apply_auto_values(details: AutoDetails, values: dict[str, Any]) -> None:
    for field_name, value in values.items():
        setattr(details, field_name, value)


def _apply_home_values(details: HomeDetails, values: dict[str, Any]) -> None:
    for field_name, value in values.items():
        setattr(details, field_name, value)


def _apply_rental_values(details: RentalDetails, values: dict[str, Any]) -> None:
    for field_name, value in values.items():
        setattr(details, field_name, value)


def _apply_ag_equipment_values(details: AgEquipmentDetails, values: dict[str, Any]) -> None:
    for field_name, value in values.items():
        setattr(details, field_name, value)


def _apply_livestock_values(details: LivestockDetails, values: dict[str, Any]) -> None:
    for field_name, value in values.items():
        setattr(details, field_name, value)


def _apply_pasture_values(details: PastureDetails, values: dict[str, Any]) -> None:
    for field_name, value in values.items():
        setattr(details, field_name, value)


def _apply_home_goods_values(details: HomeGoodsDetails, values: dict[str, Any]) -> None:
    for field_name, value in values.items():
        setattr(details, field_name, value)


def _depublish_material_edit(*, listing: Listing, seller: SellerProfile, previous: str) -> None:
    """Move an edited public listing offline only after its new typed data validates."""
    if previous != ListingStatus.PUBLISHED:
        return
    listing.status = ListingStatus.IN_REVIEW
    listing.published_at = None
    listing.last_material_edit_at = timezone.now()
    listing.lifecycle_revision += 1
    listing.save(
        update_fields=(
            "status",
            "published_at",
            "last_material_edit_at",
            "lifecycle_revision",
            "updated_at",
        )
    )
    _record_action(
        listing=listing,
        actor=seller.user,
        action_type=ModerationActionType.MATERIAL_EDIT,
        from_status=previous,
        to_status=ListingStatus.IN_REVIEW,
        seller_facing_note="Your material changes are awaiting moderation.",
    )


def _require_moderator(actor: User) -> None:
    if not actor.has_perm("listings.moderate_listing"):
        raise PermissionDenied("You do not have moderation permission.")


def _record_action(  # noqa: PLR0913
    *,
    listing: Listing,
    actor: User | None,
    action_type: ModerationActionType,
    from_status: str,
    to_status: str,
    reason_code: ModerationReasonCode | None = None,
    internal_note: str = "",
    seller_facing_note: str = "",
) -> None:
    ModerationAction.objects.create(
        listing=listing,
        actor=actor,
        action_type=action_type,
        from_status=from_status,
        to_status=to_status,
        reason_code=reason_code,
        internal_note=internal_note,
        seller_facing_note=seller_facing_note,
    )


def _enqueue_listing_notification(
    *,
    listing: Listing,
    event_type: str,
    seller_message: str = "",
) -> None:
    notification_content = {
        "listing.approved": ("Listing published", "Your listing is now published."),
        "listing.payment_ready": (
            "Listing approved — payment needed",
            "Your listing is approved. Complete the local-demo payment to publish it.",
        ),
        "listing.payment_completed": (
            "Payment complete — listing published",
            "Your local-demo payment was confirmed and your listing is now published.",
        ),
        "listing.changes_requested": (
            "Changes requested",
            "Your listing needs changes before it can be approved.",
        ),
        "listing.rejected": ("Listing not approved", "Your listing was not approved."),
        "listing.expired": ("Listing expired", "Your listing has expired."),
        "listing.sold": ("Listing marked sold", "Your listing was marked as sold."),
    }
    if content := notification_content.get(event_type):
        from apps.notifications.services import create_notification  # noqa: PLC0415

        title, default_body = content
        create_notification(
            recipient=listing.seller.user,
            event_type=event_type,
            title=title,
            body=seller_message.strip() or default_body,
            idempotency_key=f"{event_type}:{listing.id}:{listing.lifecycle_revision}",
            destination_route="listings:owner_listing_detail",
            destination_kwargs={"listing_id": str(listing.id)},
        )
    enqueue_event(
        event_type=event_type,
        payload={"listing_id": str(listing.id), "seller_message": seller_message},
        aggregate_type="listing",
        aggregate_reference=str(listing.id),
        idempotency_key=f"{event_type}:{listing.id}:{listing.lifecycle_revision}",
    )


def _expire_locked_listing(*, listing: Listing, now: datetime) -> bool:
    if (
        listing.status != ListingStatus.PUBLISHED
        or listing.expires_at is None
        or listing.expires_at > now
    ):
        return False
    previous = listing.status
    listing.status = ListingStatus.EXPIRED
    listing.published_at = None
    listing.lifecycle_revision += 1
    listing.save(update_fields=("status", "published_at", "lifecycle_revision", "updated_at"))
    _record_action(
        listing=listing,
        actor=None,
        action_type=ModerationActionType.EXPIRED,
        from_status=previous,
        to_status=ListingStatus.EXPIRED,
        seller_facing_note="Your listing has expired.",
    )
    _enqueue_listing_notification(listing=listing, event_type="listing.expired")
    return True


@transaction.atomic
def expire_due_listings(*, batch_size: int, now: datetime | None = None) -> int:
    """Transition due publications under locks; reruns and concurrent workers are safe."""
    effective_now = now or timezone.now()
    listings = list(
        Listing.objects.select_for_update(skip_locked=True)
        .filter(status=ListingStatus.PUBLISHED, expires_at__lte=effective_now)
        .order_by("expires_at")[:batch_size]
    )
    return sum(_expire_locked_listing(listing=listing, now=effective_now) for listing in listings)


@transaction.atomic
def schedule_listing_reminders(*, now: datetime | None = None) -> int:
    """Create one delayed reminder event at each selected pre-expiration offset."""
    effective_now = now or timezone.now()
    created = 0
    listings = Listing.objects.select_for_update(skip_locked=True).filter(
        status=ListingStatus.PUBLISHED,
        expires_at__gt=effective_now,
    )
    for listing in listings.iterator():
        if listing.expires_at is None:
            continue
        for days_remaining in (7, 3, 1):
            scheduled_at = listing.expires_at - timedelta(days=days_remaining)
            if scheduled_at <= effective_now:
                continue
            _event, was_created = OutboxEvent.objects.get_or_create(
                idempotency_key=(
                    f"listing.expiration_reminder:{listing.id}:{listing.expires_at.isoformat()}:"
                    f"{days_remaining}"
                ),
                defaults={
                    "event_type": "listing.expiration_reminder",
                    "payload": {
                        "listing_id": str(listing.id),
                        "days_remaining": days_remaining,
                    },
                    "aggregate_type": "listing",
                    "aggregate_reference": str(listing.id),
                    "available_at": scheduled_at,
                },
            )
            created += int(was_created)
    return created


@transaction.atomic
def transition_owned_listing(*, listing_id: UUID, seller: SellerProfile, action: str) -> Listing:
    """Perform seller-controlled terminal transitions under a row lock."""
    require_active_account(user=seller.user)
    listing = Listing.objects.select_for_update().get(pk=listing_id)
    if listing.seller_id != seller.id:
        raise PermissionDenied("Only the listing owner may manage this listing.")
    transitions: dict[str, tuple[set[str], str, ModerationActionType]] = {
        "sold": ({ListingStatus.PUBLISHED}, ListingStatus.SOLD, ModerationActionType.MARKED_SOLD),
        "archive": (
            {
                ListingStatus.DRAFT,
                ListingStatus.CHANGES_REQUESTED,
                ListingStatus.REJECTED,
                ListingStatus.SOLD,
                ListingStatus.EXPIRED,
            },
            ListingStatus.ARCHIVED,
            ModerationActionType.ARCHIVED,
        ),
        "restore_draft": (
            {ListingStatus.ARCHIVED},
            ListingStatus.DRAFT,
            ModerationActionType.RESTORED_DRAFT,
        ),
    }
    try:
        allowed, target, action_type = transitions[action]
    except KeyError as error:
        raise ValidationError("Unsupported listing action.") from error
    if listing.status not in allowed:
        raise ValidationError("This listing cannot take that action now.")
    previous = listing.status
    listing.status = target
    now = timezone.now()
    if action == "sold":
        if listing.first_published_at is None:
            listing.first_published_at = listing.published_at or now
        listing.sold_at = now
        listing.sold_public_until = now + timedelta(days=30)
    listing.published_at = None
    listing.lifecycle_revision += 1
    listing.save(
        update_fields=(
            "status",
            "published_at",
            "first_published_at",
            "sold_at",
            "sold_public_until",
            "lifecycle_revision",
            "updated_at",
        )
    )
    _record_action(
        listing=listing,
        actor=seller.user,
        action_type=action_type,
        from_status=previous,
        to_status=target,
    )
    if action == "sold":
        _enqueue_listing_notification(listing=listing, event_type="listing.sold")
    return listing


@transaction.atomic
def toggle_favorite(*, listing_id: UUID, user: User) -> bool:
    """Toggle only an active public listing; private identifiers remain unresolvable."""
    require_active_account(user=user)
    # The public selector outer-joins optional typed detail rows for presentation.
    # Lock only Listing, not those nullable join targets, on PostgreSQL.
    listing = public_listings().select_for_update(of=("self",)).filter(pk=listing_id).first()
    if listing is None:
        raise ValidationError("That listing is not available to save.")
    favorite, created = Favorite.objects.get_or_create(user=user, listing=listing)
    if not created:
        favorite.delete()
    return created


def _typed_details_for_listing(listing: Listing) -> Any:
    if listing.intent == ListingIntent.WANTED:
        try:
            return listing.generic_details
        except GenericListingDetails.DoesNotExist as error:
            raise ValidationError("Wanted listings require generic details.") from error
    try:
        return listing.generic_details
    except GenericListingDetails.DoesNotExist:
        pass
    detail_names = {
        "autos": "auto_details",
        "real-estate": "home_details",
        "rentals": "rental_details",
        "livestock-animals": "livestock_details",
        "home-garden": "home_goods_details",
        "appliances": "home_goods_details",
    }
    if listing.vertical.slug == "farm-ranch":
        for name in ("ag_equipment_details", "pasture_details"):
            try:
                return getattr(listing, name)
            except (AgEquipmentDetails.DoesNotExist, PastureDetails.DoesNotExist):
                continue
        raise ValidationError("Farm & Ranch listings require compatible typed details.")
    detail_name = detail_names.get(listing.vertical.slug)
    if detail_name is None:
        raise ValidationError("This listing vertical is not available for submission.")
    try:
        return getattr(listing, detail_name)
    except (
        AutoDetails.DoesNotExist,
        HomeDetails.DoesNotExist,
        RentalDetails.DoesNotExist,
        LivestockDetails.DoesNotExist,
        HomeGoodsDetails.DoesNotExist,
    ) as error:
        raise ValidationError("This listing requires complete typed details.") from error


def _policy_reason_codes(listing: Listing) -> list[ModerationReasonCode]:
    content = f"{listing.title} {listing.description}".lower()
    codes = [
        code
        for code, terms in POLICY_KEYWORDS.items()
        if any(re.search(rf"\b{re.escape(term)}\b", content) for term in terms)
    ]
    return list(ModerationReasonCode.objects.filter(code__in=codes, is_active=True))


def validate_submission_completeness(*, listing: Listing, seller: SellerProfile) -> None:
    """Validate a locked owner draft without changing lifecycle state."""
    require_active_account(user=seller.user)
    if listing.seller_id != seller.id:
        raise PermissionDenied("Only the listing owner may submit this listing.")
    if listing.status not in {ListingStatus.DRAFT, ListingStatus.CHANGES_REQUESTED}:
        raise ValidationError("Only drafts or listings with requested changes may be submitted.")
    listing.full_clean()
    details = _typed_details_for_listing(listing)
    details.full_clean()
    required_count, _maximum_count = image_policy_for_listing(listing=listing)
    ready_count = ListingImage.objects.filter(
        listing=listing, state=ListingImageState.READY
    ).count()
    if ready_count < required_count:
        raise ValidationError(f"Add at least {required_count} image(s) before submitting.")


@transaction.atomic
def create_generic_draft(
    *,
    seller: SellerProfile,
    listing_values: dict[str, Any],
    generic_values: dict[str, Any],
    additional_counties: list[Any],
) -> Listing:
    """Create a generic listing without selecting or creating typed detail rows."""

    require_active_account(user=seller.user)
    listing = Listing(seller=seller, vertical=listing_values["category"].vertical, **listing_values)
    listing.full_clean()
    listing.save()
    details = GenericListingDetails(listing=listing, **generic_values)
    details.full_clean()
    details.save()
    _replace_additional_counties(
        listing=listing, counties=additional_counties, postal_code=details.postal_code
    )
    return listing


@transaction.atomic
def create_wanted_draft(  # noqa: PLR0913
    *,
    seller: SellerProfile,
    listing_values: dict[str, Any],
    generic_values: dict[str, Any],
    additional_counties: list[Any],
    controlled_categories: list[Any],
    seller_tags: list[str],
    custom_fields: list[dict[str, str]],
) -> Listing:
    """Create a wanted post without a typed sale-detail or listing-kind row."""
    require_active_account(user=seller.user)
    category = listing_values["category"]
    listing = Listing(
        seller=seller,
        intent=ListingIntent.WANTED,
        vertical=category.vertical,
        **listing_values,
    )
    listing.full_clean()
    listing.save()
    details = GenericListingDetails(listing=listing, **generic_values)
    details.full_clean()
    details.save()
    _replace_additional_counties(
        listing=listing, counties=additional_counties, postal_code=details.postal_code
    )
    _replace_listing_taxonomy_and_facts(
        listing=listing,
        controlled_categories=controlled_categories,
        seller_tags=seller_tags,
        custom_fields=custom_fields,
    )
    return listing


@transaction.atomic
def create_unified_draft(  # noqa: PLR0913
    *,
    seller: SellerProfile,
    workflow: ListingWorkflow,
    listing_values: dict[str, Any],
    detail_values: dict[str, Any],
    generic_values: dict[str, Any] | None = None,
    additional_counties: list[Any] | None = None,
    controlled_categories: list[Any] | None = None,
    seller_tags: list[str] | None = None,
    custom_fields: list[dict[str, str]] | None = None,
) -> Listing:
    """Create exactly one server-resolved detail representation for a listing."""

    require_active_account(user=seller.user)
    if not workflow.typed:
        assert generic_values is not None
        listing = create_generic_draft(
            seller=seller,
            listing_values=listing_values,
            generic_values=generic_values,
            additional_counties=additional_counties or [],
        )
        _replace_listing_taxonomy_and_facts(
            listing=listing,
            controlled_categories=controlled_categories or [],
            seller_tags=seller_tags or [],
            custom_fields=custom_fields or [],
        )
        return listing
    creators: dict[str, Callable[[], Listing]] = {
        "auto": lambda: create_auto_draft(
            seller=seller, listing_values=listing_values, auto_values=detail_values
        ),
        "home": lambda: create_home_draft(
            seller=seller, listing_values=listing_values, home_values=detail_values
        ),
        "rental": lambda: create_rental_draft(
            seller=seller, listing_values=listing_values, rental_values=detail_values
        ),
        "ag_equipment": lambda: create_ag_equipment_draft(
            seller=seller, listing_values=listing_values, ag_equipment_values=detail_values
        ),
        "livestock": lambda: create_livestock_draft(
            seller=seller, listing_values=listing_values, livestock_values=detail_values
        ),
        "pasture": lambda: create_pasture_draft(
            seller=seller, listing_values=listing_values, pasture_values=detail_values
        ),
        "home_goods": lambda: (
            create_appliances_draft(
                seller=seller, listing_values=listing_values, home_goods_values=detail_values
            )
            if listing_values["category"].vertical.slug == "appliances"
            else create_home_garden_draft(
                seller=seller, listing_values=listing_values, home_goods_values=detail_values
            )
        ),
    }
    try:
        listing = creators[workflow.key]()
    except KeyError as error:
        raise ValidationError("Unsupported listing workflow.") from error
    _replace_listing_taxonomy_and_facts(
        listing=listing,
        controlled_categories=controlled_categories or [],
        seller_tags=seller_tags or [],
        custom_fields=custom_fields or [],
    )
    return listing


@transaction.atomic
def update_generic_draft(
    *,
    listing_id: UUID,
    seller: SellerProfile,
    listing_values: dict[str, Any],
    generic_values: dict[str, Any],
    additional_counties: list[Any],
) -> Listing:
    """Update the bounded generic data and distribution under one owner lock."""

    require_active_account(user=seller.user)
    listing = (
        Listing.objects.select_for_update()
        .select_related("seller", "vertical", "generic_details")
        .get(pk=listing_id)
    )
    if listing.seller_id != seller.id:
        raise PermissionDenied("Only the listing owner may edit this draft.")
    if listing.status not in OWNER_EDITABLE_STATUSES:
        raise PermissionDenied("Only draft, changed, or published listings may be edited.")
    previous = listing.status
    _apply_listing_values(listing, listing_values)
    listing.vertical = listing.category.vertical
    listing.full_clean()
    listing.save()
    details = listing.generic_details
    for field_name, value in generic_values.items():
        setattr(details, field_name, value)
    details.full_clean()
    details.save()
    _replace_additional_counties(
        listing=listing, counties=additional_counties, postal_code=details.postal_code
    )
    _depublish_material_edit(listing=listing, seller=seller, previous=previous)
    return listing


@transaction.atomic
def update_unified_listing(  # noqa: PLR0913
    *,
    listing_id: UUID,
    seller: SellerProfile,
    workflow: ListingWorkflow,
    listing_values: dict[str, Any],
    detail_values: dict[str, Any],
    generic_values: dict[str, Any] | None = None,
    additional_counties: list[Any] | None = None,
    controlled_categories: list[Any],
    seller_tags: list[str],
    custom_fields: list[dict[str, str]],
) -> Listing:
    """Update one existing listing representation under its owner row lock.

    The workflow and profile are resolved by the server from the persisted primary
    category. This service never creates a different detail representation.
    """
    require_active_account(user=seller.user)
    listing = (
        Listing.objects.select_for_update()
        .select_related("category", "vertical", "seller")
        .get(pk=listing_id)
    )
    if listing.seller_id != seller.id:
        raise PermissionDenied("Only the listing owner may edit this listing.")
    if listing.status not in OWNER_EDITABLE_STATUSES:
        raise PermissionDenied("Only draft, changed, or published listings may be edited.")

    persisted_workflow = resolve_listing_workflow(category=listing.category, intent=listing.intent)
    if persisted_workflow != workflow:
        raise ValidationError("The listing workflow changed. Reload and retry.")
    previous = listing.status
    _apply_listing_values(listing, listing_values)
    listing.vertical = listing.category.vertical
    listing.full_clean()
    listing.save()

    if workflow.typed:
        detail_models: dict[str, tuple[type[Any], Callable[[Any, dict[str, Any]], None]]] = {
            "auto": (AutoDetails, _apply_auto_values),
            "home": (HomeDetails, _apply_home_values),
            "rental": (RentalDetails, _apply_rental_values),
            "ag_equipment": (AgEquipmentDetails, _apply_ag_equipment_values),
            "livestock": (LivestockDetails, _apply_livestock_values),
            "pasture": (PastureDetails, _apply_pasture_values),
            "home_goods": (HomeGoodsDetails, _apply_home_goods_values),
        }
        try:
            detail_model, apply_values = detail_models[workflow.key]
            details = detail_model.objects.select_for_update().get(listing=listing)
        except (
            KeyError,
            AutoDetails.DoesNotExist,
            HomeDetails.DoesNotExist,
            RentalDetails.DoesNotExist,
            AgEquipmentDetails.DoesNotExist,
            LivestockDetails.DoesNotExist,
            PastureDetails.DoesNotExist,
            HomeGoodsDetails.DoesNotExist,
        ) as error:
            raise ValidationError("This listing has no compatible typed details.") from error
        apply_values(details, detail_values)
        details.full_clean()
        details.save()
    else:
        if generic_values is None:
            raise ValidationError("Generic listing details are required.")
        try:
            details = GenericListingDetails.objects.select_for_update().get(listing=listing)
        except GenericListingDetails.DoesNotExist as error:
            raise ValidationError("This listing has no compatible generic details.") from error
        for field_name, value in generic_values.items():
            setattr(details, field_name, value)
        details.full_clean()
        details.save()
        _replace_additional_counties(
            listing=listing,
            counties=additional_counties or [],
            postal_code=details.postal_code,
        )

    _replace_listing_taxonomy_and_facts(
        listing=listing,
        controlled_categories=controlled_categories,
        seller_tags=seller_tags,
        custom_fields=custom_fields,
    )
    _depublish_material_edit(listing=listing, seller=seller, previous=previous)
    return listing


def _replace_additional_counties(
    *, listing: Listing, counties: list[Any], postal_code: str
) -> None:
    """Validate candidate scope while the caller holds the listing transaction."""

    candidate_ids = {
        county.id
        for county in zip_county_candidates(postal_code=postal_code, state_id=listing.state_id)
    }
    selected_ids = {county.id for county in counties}
    if listing.county_id not in candidate_ids or not selected_ids.issubset(candidate_ids):
        raise ValidationError("All selected counties must be offline ZIP-to-county candidates.")
    if listing.county_id in selected_ids:
        raise ValidationError("The primary county cannot be selected as an additional county.")
    ListingCountyPlacement.objects.filter(listing=listing).delete()
    placements = [ListingCountyPlacement(listing=listing, county=county) for county in counties]
    for placement in placements:
        placement.full_clean()
    ListingCountyPlacement.objects.bulk_create(placements)


def _uses_local_demo_billing(listing: Listing) -> bool:
    """Keep production submission unchanged until a production adapter is approved."""
    now = timezone.now()
    return bool(
        settings.DEBUG
        and listing.vertical.slug == "autos"
        and listing.price_minor is not None
        and listing.listing_kind_id is not None
        and ListingProduct.objects.filter(
            product_code="AUTOS_NEW_FIXED",
            listing_kind_id=listing.listing_kind_id,
            is_active=True,
            prices__currency="USD",
            prices__amount_minor=1000,
            prices__effective_from__lte=now,
        )
        .filter(
            models.Q(prices__effective_until__isnull=True)
            | models.Q(prices__effective_until__gt=now)
        )
        .exists()
    )


def _create_generic_quote_if_configured(*, listing: Listing) -> None:
    """Quotes are demonstrative only: missing local config never blocks moderation."""

    if not settings.DEBUG:
        return
    try:
        GenericListingDetails.objects.get(listing=listing)
    except GenericListingDetails.DoesNotExist:
        return
    from apps.billing.services import (  # noqa: PLC0415
        BillingError,
        create_generic_distribution_quote,
    )

    try:
        create_generic_distribution_quote(listing_id=listing.id, seller_id=listing.seller_id)
    except (BillingError, ListingProduct.DoesNotExist):
        return


@transaction.atomic
def submit_listing(*, listing_id: UUID, seller: SellerProfile) -> Listing:
    # Lock only the listing row. `listing_kind` is nullable, so combining a
    # broad select_related() with FOR UPDATE produces a PostgreSQL outer join
    # that PostgreSQL correctly refuses to lock.
    listing = Listing.objects.select_for_update().get(pk=listing_id)
    validate_submission_completeness(listing=listing, seller=seller)
    require_current_listing_acceptances(user=seller.user, listing=listing)
    previous = listing.status
    listing.status = ListingStatus.SUBMITTED
    listing.lifecycle_revision += 1
    listing.save(update_fields=("status", "lifecycle_revision", "updated_at"))
    _record_action(
        listing=listing,
        actor=seller.user,
        action_type=ModerationActionType.SUBMITTED,
        from_status=previous,
        to_status=ListingStatus.SUBMITTED,
    )
    listing.status = ListingStatus.IN_REVIEW
    listing.lifecycle_revision += 1
    listing.save(update_fields=("status", "lifecycle_revision", "updated_at"))
    _record_action(
        listing=listing,
        actor=None,
        action_type=ModerationActionType.SUBMITTED,
        from_status=ListingStatus.SUBMITTED,
        to_status=ListingStatus.IN_REVIEW,
    )
    for reason in _policy_reason_codes(listing):
        _record_action(
            listing=listing,
            actor=None,
            action_type=ModerationActionType.POLICY_FLAGGED,
            from_status=ListingStatus.IN_REVIEW,
            to_status=ListingStatus.IN_REVIEW,
            reason_code=reason,
            internal_note="Deterministic keyword scanner flag; staff review required.",
        )
    return listing


@transaction.atomic
def accept_policies_and_submit_listing(*, listing_id: UUID, seller: SellerProfile) -> Listing:
    """Accept the server-selected active policy set before submitting one listing."""
    listing = Listing.objects.select_for_update().select_related("seller").get(pk=listing_id)
    if listing.seller_id != seller.id:
        raise PermissionDenied("Only the listing owner may submit this listing.")
    accept_current_listing_policies(user=seller.user, listing=listing)
    return submit_listing(listing_id=listing_id, seller=seller)


def _locked_moderation_listing(*, listing_id: UUID, actor: User, revision: int) -> Listing:
    _require_moderator(actor)
    listing = Listing.objects.select_for_update().get(pk=listing_id)
    if listing.lifecycle_revision != revision:
        raise ValidationError("This review is stale. Refresh the queue and try again.")
    return listing


@transaction.atomic
def claim_listing(*, listing_id: UUID, actor: User, revision: int) -> Listing:
    listing = _locked_moderation_listing(listing_id=listing_id, actor=actor, revision=revision)
    if listing.status != ListingStatus.IN_REVIEW:
        raise ValidationError("Only listings in review can be claimed.")
    if listing.assigned_moderator_id not in {None, actor.id}:
        raise ValidationError("This review is already assigned to another moderator.")
    listing.assigned_moderator = actor
    listing.lifecycle_revision += 1
    listing.save(update_fields=("assigned_moderator", "lifecycle_revision", "updated_at"))
    _record_action(
        listing=listing,
        actor=actor,
        action_type=ModerationActionType.CLAIMED,
        from_status=listing.status,
        to_status=listing.status,
    )
    return listing


def _require_negative_reason(reason_code: ModerationReasonCode | None) -> ModerationReasonCode:
    if reason_code is None or not reason_code.is_active:
        raise ValidationError("An active moderation reason code is required.")
    return reason_code


def _apply_image_moderation(
    *,
    listing: Listing,
    actor: User,
    image_decisions: dict[UUID, tuple[ListingImageModerationStatus, str]],
) -> None:
    """Apply explicit staff decisions without conflating storage and review state."""
    ready_images = list(
        ListingImage.objects.select_for_update()
        .filter(listing=listing, state=ListingImageState.READY)
        .order_by("ordering")
    )
    pending_ids = {
        image.id
        for image in ready_images
        if image.moderation_status == ListingImageModerationStatus.PENDING
    }
    if pending_ids != set(image_decisions):
        raise ValidationError("Every pending image requires an approval or rejection decision.")
    for image in ready_images:
        decision = image_decisions.get(image.id)
        if decision is None:
            continue
        moderation_status, seller_reason = decision
        if moderation_status == ListingImageModerationStatus.REJECTED and not seller_reason.strip():
            raise ValidationError("Rejected images require a seller-visible reason.")
        image.moderation_status = moderation_status
        image.moderation_reason = seller_reason.strip()
        image.moderated_at = timezone.now()
        image.moderated_by = actor
        image.save(
            update_fields=(
                "moderation_status",
                "moderation_reason",
                "moderated_at",
                "moderated_by",
            )
        )
        _record_action(
            listing=listing,
            actor=actor,
            action_type=(
                ModerationActionType.IMAGE_APPROVED
                if moderation_status == ListingImageModerationStatus.APPROVED
                else ModerationActionType.IMAGE_REJECTED
            ),
            from_status=listing.status,
            to_status=listing.status,
            seller_facing_note=image.moderation_reason,
        )


def _apply_video_moderation(
    *,
    listing: Listing,
    actor: User,
    video_decisions: dict[UUID, tuple[ListingVideoModerationStatus, str]],
) -> None:
    """Apply a separate review decision to every pending supplemental video."""
    ready_videos = list(
        ListingVideo.objects.select_for_update()
        .filter(listing=listing, state=ListingVideoState.READY)
        .order_by("created_at")
    )
    pending_ids = {
        video.id
        for video in ready_videos
        if video.moderation_status == ListingVideoModerationStatus.PENDING
    }
    if pending_ids != set(video_decisions):
        raise ValidationError("Every pending video requires an approval or rejection decision.")
    for video in ready_videos:
        decision = video_decisions.get(video.id)
        if decision is None:
            continue
        moderation_status, seller_reason = decision
        if moderation_status == ListingVideoModerationStatus.REJECTED and not seller_reason.strip():
            raise ValidationError("Rejected videos require a seller-visible reason.")
        video.moderation_status = moderation_status
        video.moderation_reason = seller_reason.strip()
        video.moderated_at = timezone.now()
        video.moderated_by = actor
        video.save(
            update_fields=(
                "moderation_status",
                "moderation_reason",
                "moderated_at",
                "moderated_by",
            )
        )
        _record_action(
            listing=listing,
            actor=actor,
            action_type=(
                ModerationActionType.VIDEO_APPROVED
                if moderation_status == ListingVideoModerationStatus.APPROVED
                else ModerationActionType.VIDEO_REJECTED
            ),
            from_status=listing.status,
            to_status=listing.status,
            seller_facing_note=video.moderation_reason,
        )


def _has_required_approved_images(*, listing: Listing) -> bool:
    required_count, _maximum_count = image_policy_for_listing(listing=listing)
    approved_count = ListingImage.objects.filter(
        listing=listing,
        state=ListingImageState.READY,
        moderation_status=ListingImageModerationStatus.APPROVED,
    ).count()
    return approved_count >= required_count


@transaction.atomic
def moderate_listing(  # noqa: PLR0912, PLR0913
    *,
    listing_id: UUID,
    actor: User,
    revision: int,
    outcome: ModerationActionType,
    reason_code: ModerationReasonCode | None = None,
    internal_note: str = "",
    seller_facing_note: str = "",
    image_decisions: dict[UUID, tuple[ListingImageModerationStatus, str]] | None = None,
    video_decisions: dict[UUID, tuple[ListingVideoModerationStatus, str]] | None = None,
) -> Listing:
    listing = _locked_moderation_listing(listing_id=listing_id, actor=actor, revision=revision)
    transitions = {
        ModerationActionType.APPROVED: ListingStatus.PUBLISHED,
        ModerationActionType.APPROVED_NO_PAYMENT: ListingStatus.PUBLISHED,
        ModerationActionType.APPROVED_SEND_PAYMENT_LINK: ListingStatus.AWAITING_PAYMENT,
        ModerationActionType.CHANGES_REQUESTED: ListingStatus.CHANGES_REQUESTED,
        ModerationActionType.REJECTED: ListingStatus.REJECTED,
        ModerationActionType.SUSPENDED: ListingStatus.SUSPENDED,
    }
    if outcome not in transitions:
        raise ValidationError("Unsupported moderation outcome.")
    if outcome == ModerationActionType.SUSPENDED:
        if listing.status not in {ListingStatus.IN_REVIEW, ListingStatus.PUBLISHED}:
            raise ValidationError("Only published or in-review listings can be suspended.")
    elif outcome == ModerationActionType.REJECTED and listing.status == ListingStatus.PUBLISHED:
        pass
    elif listing.status != ListingStatus.IN_REVIEW:
        raise ValidationError("Only listings in review can receive this outcome.")
    if outcome in {
        ModerationActionType.CHANGES_REQUESTED,
        ModerationActionType.REJECTED,
        ModerationActionType.SUSPENDED,
    }:
        reason_code = _require_negative_reason(reason_code)
    _apply_image_moderation(
        listing=listing,
        actor=actor,
        image_decisions=image_decisions or {},
    )
    _apply_video_moderation(
        listing=listing,
        actor=actor,
        video_decisions=video_decisions or {},
    )
    effective_outcome = outcome
    if outcome in {
        ModerationActionType.APPROVED,
        ModerationActionType.APPROVED_NO_PAYMENT,
        ModerationActionType.APPROVED_SEND_PAYMENT_LINK,
    } and not _has_required_approved_images(listing=listing):
        effective_outcome = ModerationActionType.CHANGES_REQUESTED
        reason_code = _require_negative_reason(reason_code)
        if not seller_facing_note.strip():
            seller_facing_note = "Add enough approved images to meet this category's requirement."
    previous = listing.status
    listing.status = transitions[effective_outcome]
    listing.assigned_moderator = actor
    if listing.status == ListingStatus.PUBLISHED:
        _mark_published(listing=listing, published_at=timezone.now())
        listing.last_material_edit_at = None
        paid_line = (
            listing.orders.filter(status=OrderStatus.PAID)
            .prefetch_related("lines")
            .order_by("-paid_at")
            .first()
        )
        if paid_line is not None:
            duration = paid_line.lines.get().duration_days
            assert listing.published_at is not None
            listing.expires_at = listing.published_at + timedelta(days=duration)
    else:
        listing.published_at = None
    listing.lifecycle_revision += 1
    listing.save(
        update_fields=(
            "status",
            "assigned_moderator",
            "published_at",
            "first_published_at",
            "expires_at",
            "last_material_edit_at",
            "lifecycle_revision",
            "updated_at",
        )
    )
    if effective_outcome == ModerationActionType.APPROVED_SEND_PAYMENT_LINK:
        if not settings.DEBUG:
            raise ValidationError("The local-demo payment link is only available in DEBUG mode.")
        create_checkout_order(listing_id=listing.id, seller_id=listing.seller_id)
    if listing.status == ListingStatus.PUBLISHED:
        rebuild_public_search_document(listing=listing)
    _record_action(
        listing=listing,
        actor=actor,
        action_type=effective_outcome,
        from_status=previous,
        to_status=listing.status,
        reason_code=reason_code,
        internal_note=internal_note,
        seller_facing_note=seller_facing_note,
    )
    if effective_outcome == ModerationActionType.REJECTED:
        # The local adapter owns payment truth; no browser route can initiate this transition.
        refund_rejected_listing(listing_id=listing.id)
    notification_events = {
        ModerationActionType.APPROVED: "listing.approved",
        ModerationActionType.APPROVED_NO_PAYMENT: "listing.approved",
        ModerationActionType.APPROVED_SEND_PAYMENT_LINK: "listing.payment_ready",
        ModerationActionType.CHANGES_REQUESTED: "listing.changes_requested",
        ModerationActionType.REJECTED: "listing.rejected",
    }
    if event_type := notification_events.get(effective_outcome):
        _enqueue_listing_notification(
            listing=listing,
            event_type=event_type,
            seller_message=seller_facing_note,
        )
    return listing


@transaction.atomic
def create_auto_draft(
    *,
    seller: SellerProfile,
    listing_values: dict[str, Any],
    auto_values: dict[str, Any],
) -> Listing:
    listing = Listing(
        seller=seller,
        vertical=_autos_vertical(),
        listing_kind=_autos_listing_kind(),
        **listing_values,
    )
    listing.full_clean()
    listing.save()

    details = AutoDetails(listing=listing, **auto_values)
    details.full_clean()
    details.save()
    return listing


@transaction.atomic
def update_auto_draft(
    *,
    listing_id: UUID,
    seller: SellerProfile,
    listing_values: dict[str, Any],
    auto_values: dict[str, Any],
) -> Listing:
    listing = Listing.objects.select_for_update().select_related("seller").get(pk=listing_id)
    if listing.seller_id != seller.id:
        raise PermissionDenied("Only the listing owner may edit this draft.")
    if listing.status not in OWNER_EDITABLE_STATUSES:
        raise PermissionDenied("Only draft, changed, or published listings may be edited.")
    previous = listing.status

    _apply_listing_values(listing, listing_values)
    listing.full_clean()
    listing.save()

    details, _created = AutoDetails.objects.select_for_update().get_or_create(listing=listing)
    _apply_auto_values(details, auto_values)
    details.full_clean()
    details.save()
    _depublish_material_edit(listing=listing, seller=seller, previous=previous)
    return listing


@transaction.atomic
def create_home_draft(
    *,
    seller: SellerProfile,
    listing_values: dict[str, Any],
    home_values: dict[str, Any],
) -> Listing:
    listing = Listing(seller=seller, vertical=_homes_vertical(), **listing_values)
    listing.full_clean()
    listing.save()
    details = HomeDetails(listing=listing, **home_values)
    details.full_clean()
    details.save()
    return listing


@transaction.atomic
def update_home_draft(
    *,
    listing_id: UUID,
    seller: SellerProfile,
    listing_values: dict[str, Any],
    home_values: dict[str, Any],
) -> Listing:
    listing = Listing.objects.select_for_update().select_related("seller").get(pk=listing_id)
    if listing.seller_id != seller.id:
        raise PermissionDenied("Only the listing owner may edit this draft.")
    if listing.status not in OWNER_EDITABLE_STATUSES:
        raise PermissionDenied("Only draft, changed, or published listings may be edited.")
    previous = listing.status
    if listing.vertical.slug != "real-estate":
        raise ValidationError("Only Home drafts may be updated by this service.")
    _apply_listing_values(listing, listing_values)
    listing.full_clean()
    listing.save()
    details, _created = HomeDetails.objects.select_for_update().get_or_create(listing=listing)
    _apply_home_values(details, home_values)
    details.full_clean()
    details.save()
    _depublish_material_edit(listing=listing, seller=seller, previous=previous)
    return listing


@transaction.atomic
def create_rental_draft(
    *,
    seller: SellerProfile,
    listing_values: dict[str, Any],
    rental_values: dict[str, Any],
) -> Listing:
    listing = Listing(seller=seller, vertical=_rentals_vertical(), **listing_values)
    listing.full_clean()
    listing.save()
    details = RentalDetails(listing=listing, **rental_values)
    details.full_clean()
    details.save()
    return listing


@transaction.atomic
def update_rental_draft(
    *,
    listing_id: UUID,
    seller: SellerProfile,
    listing_values: dict[str, Any],
    rental_values: dict[str, Any],
) -> Listing:
    listing = Listing.objects.select_for_update().select_related("seller").get(pk=listing_id)
    if listing.seller_id != seller.id:
        raise PermissionDenied("Only the listing owner may edit this draft.")
    if listing.status not in OWNER_EDITABLE_STATUSES:
        raise PermissionDenied("Only draft, changed, or published listings may be edited.")
    previous = listing.status
    if listing.vertical.slug != "rentals":
        raise ValidationError("Only Rental drafts may be updated by this service.")
    _apply_listing_values(listing, listing_values)
    listing.full_clean()
    listing.save()
    details, _created = RentalDetails.objects.select_for_update().get_or_create(listing=listing)
    _apply_rental_values(details, rental_values)
    details.full_clean()
    details.save()
    _depublish_material_edit(listing=listing, seller=seller, previous=previous)
    return listing


@transaction.atomic
def create_ag_equipment_draft(
    *,
    seller: SellerProfile,
    listing_values: dict[str, Any],
    ag_equipment_values: dict[str, Any],
) -> Listing:
    listing = Listing(seller=seller, vertical=_farm_ranch_vertical(), **listing_values)
    listing.full_clean()
    listing.save()
    details = AgEquipmentDetails(listing=listing, **ag_equipment_values)
    details.full_clean()
    details.save()
    return listing


@transaction.atomic
def update_ag_equipment_draft(
    *,
    listing_id: UUID,
    seller: SellerProfile,
    listing_values: dict[str, Any],
    ag_equipment_values: dict[str, Any],
) -> Listing:
    listing = (
        Listing.objects.select_for_update().select_related("seller", "vertical").get(pk=listing_id)
    )
    if listing.seller_id != seller.id:
        raise PermissionDenied("Only the listing owner may edit this draft.")
    if listing.status not in OWNER_EDITABLE_STATUSES:
        raise PermissionDenied("Only draft, changed, or published listings may be edited.")
    previous = listing.status
    if listing.vertical.slug != "farm-ranch":
        raise ValidationError("Only Agricultural Equipment drafts may be updated by this service.")
    _apply_listing_values(listing, listing_values)
    listing.full_clean()
    listing.save()
    details, _created = AgEquipmentDetails.objects.select_for_update().get_or_create(
        listing=listing
    )
    _apply_ag_equipment_values(details, ag_equipment_values)
    details.full_clean()
    details.save()
    _depublish_material_edit(listing=listing, seller=seller, previous=previous)
    return listing


@transaction.atomic
def create_livestock_draft(
    *,
    seller: SellerProfile,
    listing_values: dict[str, Any],
    livestock_values: dict[str, Any],
) -> Listing:
    listing = Listing(seller=seller, vertical=_livestock_vertical(), **listing_values)
    listing.full_clean()
    listing.save()
    details = LivestockDetails(listing=listing, **livestock_values)
    details.full_clean()
    details.save()
    return listing


@transaction.atomic
def update_livestock_draft(
    *,
    listing_id: UUID,
    seller: SellerProfile,
    listing_values: dict[str, Any],
    livestock_values: dict[str, Any],
) -> Listing:
    listing = (
        Listing.objects.select_for_update().select_related("seller", "vertical").get(pk=listing_id)
    )
    if listing.seller_id != seller.id:
        raise PermissionDenied("Only the listing owner may edit this draft.")
    if listing.status not in OWNER_EDITABLE_STATUSES:
        raise PermissionDenied("Only draft, changed, or published listings may be edited.")
    previous = listing.status
    if listing.vertical.slug != "livestock-animals":
        raise ValidationError("Only Livestock drafts may be updated by this service.")
    _apply_listing_values(listing, listing_values)
    listing.full_clean()
    listing.save()
    details, _created = LivestockDetails.objects.select_for_update().get_or_create(listing=listing)
    _apply_livestock_values(details, livestock_values)
    details.full_clean()
    details.save()
    _depublish_material_edit(listing=listing, seller=seller, previous=previous)
    return listing


@transaction.atomic
def create_pasture_draft(
    *,
    seller: SellerProfile,
    listing_values: dict[str, Any],
    pasture_values: dict[str, Any],
) -> Listing:
    listing = Listing(seller=seller, vertical=_farm_ranch_vertical(), **listing_values)
    listing.full_clean()
    listing.save()
    details = PastureDetails(listing=listing, **pasture_values)
    details.full_clean()
    details.save()
    return listing


@transaction.atomic
def update_pasture_draft(
    *,
    listing_id: UUID,
    seller: SellerProfile,
    listing_values: dict[str, Any],
    pasture_values: dict[str, Any],
) -> Listing:
    listing = (
        Listing.objects.select_for_update().select_related("seller", "vertical").get(pk=listing_id)
    )
    if listing.seller_id != seller.id:
        raise PermissionDenied("Only the listing owner may edit this draft.")
    if listing.status not in OWNER_EDITABLE_STATUSES:
        raise PermissionDenied("Only draft, changed, or published listings may be edited.")
    previous = listing.status
    if listing.vertical.slug != "farm-ranch":
        raise ValidationError("Only Pasture drafts may be updated by this service.")
    _apply_listing_values(listing, listing_values)
    listing.full_clean()
    listing.save()
    details, _created = PastureDetails.objects.select_for_update().get_or_create(listing=listing)
    _apply_pasture_values(details, pasture_values)
    details.full_clean()
    details.save()
    _depublish_material_edit(listing=listing, seller=seller, previous=previous)
    return listing


@transaction.atomic
def create_home_garden_draft(
    *,
    seller: SellerProfile,
    listing_values: dict[str, Any],
    home_goods_values: dict[str, Any],
) -> Listing:
    listing = Listing(seller=seller, vertical=_home_garden_vertical(), **listing_values)
    listing.full_clean()
    listing.save()
    details = HomeGoodsDetails(listing=listing, **home_goods_values)
    details.full_clean()
    details.save()
    return listing


@transaction.atomic
def update_home_garden_draft(
    *,
    listing_id: UUID,
    seller: SellerProfile,
    listing_values: dict[str, Any],
    home_goods_values: dict[str, Any],
) -> Listing:
    listing = (
        Listing.objects.select_for_update().select_related("seller", "vertical").get(pk=listing_id)
    )
    if listing.seller_id != seller.id:
        raise PermissionDenied("Only the listing owner may edit this draft.")
    if listing.status not in OWNER_EDITABLE_STATUSES:
        raise PermissionDenied("Only draft, changed, or published listings may be edited.")
    previous = listing.status
    if listing.vertical.slug != "home-garden":
        raise ValidationError("Only Home & Garden drafts may be updated by this service.")
    _apply_listing_values(listing, listing_values)
    listing.full_clean()
    listing.save()
    details, _created = HomeGoodsDetails.objects.select_for_update().get_or_create(listing=listing)
    _apply_home_goods_values(details, home_goods_values)
    details.full_clean()
    details.save()
    _depublish_material_edit(listing=listing, seller=seller, previous=previous)
    return listing


@transaction.atomic
def create_appliances_draft(
    *,
    seller: SellerProfile,
    listing_values: dict[str, Any],
    home_goods_values: dict[str, Any],
) -> Listing:
    listing = Listing(seller=seller, vertical=_appliances_vertical(), **listing_values)
    listing.full_clean()
    listing.save()
    details = HomeGoodsDetails(listing=listing, **home_goods_values)
    details.full_clean()
    details.save()
    return listing


@transaction.atomic
def update_appliances_draft(
    *,
    listing_id: UUID,
    seller: SellerProfile,
    listing_values: dict[str, Any],
    home_goods_values: dict[str, Any],
) -> Listing:
    listing = (
        Listing.objects.select_for_update().select_related("seller", "vertical").get(pk=listing_id)
    )
    if listing.seller_id != seller.id:
        raise PermissionDenied("Only the listing owner may edit this draft.")
    if listing.status not in OWNER_EDITABLE_STATUSES:
        raise PermissionDenied("Only draft, changed, or published listings may be edited.")
    previous = listing.status
    if listing.vertical.slug != "appliances":
        raise ValidationError("Only Appliances drafts may be updated by this service.")
    _apply_listing_values(listing, listing_values)
    listing.full_clean()
    listing.save()
    details, _created = HomeGoodsDetails.objects.select_for_update().get_or_create(listing=listing)
    _apply_home_goods_values(details, home_goods_values)
    details.full_clean()
    details.save()
    _depublish_material_edit(listing=listing, seller=seller, previous=previous)
    return listing


def publish_auto_listing(*, listing_id: UUID) -> Listing:
    """Staff/demo-only legacy direct approval path; seller requests use submit_listing."""
    with transaction.atomic():
        return _publish_auto_listing_direct(listing_id=listing_id)


@transaction.atomic
def publish_demo_listing(*, listing_id: UUID) -> Listing:
    """DEBUG fixture system approval path with a durable moderation audit event."""
    listing = (
        Listing.objects.select_for_update()
        .select_related("vertical", "category", "state", "county")
        .get(pk=listing_id)
    )
    if listing.status == ListingStatus.PUBLISHED:
        return listing
    if listing.status != ListingStatus.DRAFT:
        raise ValidationError("Only draft demo listings may be directly approved.")
    if not (
        listing.vertical.is_active
        and listing.category.is_active
        and listing.state.is_active
        and listing.state.is_network_enabled
        and listing.county.is_active
        and listing.county.is_network_enabled
    ):
        raise ValidationError("Published listings require active, network-enabled references.")
    details = _typed_details_for_listing(listing)
    listing.full_clean()
    details.full_clean()
    listing.status = ListingStatus.PUBLISHED
    _mark_published(listing=listing, published_at=timezone.now())
    listing.lifecycle_revision += 1
    listing.full_clean()
    listing.save(
        update_fields=(
            "status",
            "published_at",
            "first_published_at",
            "lifecycle_revision",
            "updated_at",
        )
    )
    rebuild_public_search_document(listing=listing)
    _record_action(
        listing=listing,
        actor=None,
        action_type=ModerationActionType.DIRECT_APPROVAL,
        from_status=ListingStatus.DRAFT,
        to_status=ListingStatus.PUBLISHED,
        internal_note="DEBUG nationwide demo system approval.",
    )
    return listing


def _publish_auto_listing_direct(*, listing_id: UUID) -> Listing:
    listing = (
        Listing.objects.select_for_update()
        .select_related("vertical", "category", "state", "county")
        .get(pk=listing_id)
    )
    if listing.status != ListingStatus.DRAFT:
        raise ValidationError("Only draft listings may be published.")
    try:
        details = AutoDetails.objects.select_for_update().get(listing=listing)
    except AutoDetails.DoesNotExist as error:
        raise ValidationError("Autos listings require complete vehicle details.") from error

    if listing.vertical.slug != "autos":
        raise ValidationError("Only Autos listings may be published by this service.")
    if not (
        listing.vertical.is_active
        and listing.category.is_active
        and listing.state.is_active
        and listing.state.is_network_enabled
        and listing.county.is_active
        and listing.county.is_network_enabled
    ):
        raise ValidationError("Published listings require active, network-enabled references.")

    listing.full_clean()
    details.full_clean()
    listing.status = ListingStatus.PUBLISHED
    _mark_published(listing=listing, published_at=timezone.now())
    listing.lifecycle_revision += 1
    listing.full_clean()
    listing.save(
        update_fields=(
            "status",
            "published_at",
            "first_published_at",
            "lifecycle_revision",
            "updated_at",
        )
    )
    rebuild_public_search_document(listing=listing)
    _record_action(
        listing=listing,
        actor=None,
        action_type=ModerationActionType.DIRECT_APPROVAL,
        from_status=ListingStatus.DRAFT,
        to_status=ListingStatus.PUBLISHED,
        internal_note="Legacy staff/demo fixture direct approval path.",
    )
    return listing


def image_policy_for_listing(*, listing: Listing) -> tuple[int, int]:
    """Return category override, then ListingKind policy, then safe no-minimum defaults."""
    policy = ListingMediaPolicy.objects.filter(category_id=listing.category_id).first()
    if policy is None and listing.listing_kind_id:
        policy = ListingMediaPolicy.objects.filter(listing_kind_id=listing.listing_kind_id).first()
    if policy is None:
        return (0, DEFAULT_MAXIMUM_IMAGE_COUNT)
    return (policy.required_image_count, policy.maximum_image_count)


def _locked_owned_draft(*, listing_id: UUID, seller: SellerProfile) -> Listing:
    listing = Listing.objects.select_for_update().select_related("category").get(pk=listing_id)
    if listing.seller_id != seller.id or listing.status not in OWNER_EDITABLE_STATUSES:
        raise PermissionDenied(
            "Only the owner may change draft, changed, or published listing media."
        )
    return listing


@transaction.atomic
def begin_image_upload(
    *, listing_id: UUID, seller: SellerProfile, original_filename: str
) -> UploadSession:
    if not settings.LISTING_MEDIA_ENABLED:
        raise ValidationError("Listing image uploads are not configured in this environment.")
    listing = _locked_owned_draft(listing_id=listing_id, seller=seller)
    _required_count, maximum_count = image_policy_for_listing(listing=listing)
    if (
        ListingImage.objects.filter(listing=listing, state=ListingImageState.READY).count()
        >= maximum_count
    ):
        raise ValidationError("This draft has reached its image limit.")
    return UploadSession.objects.create(
        listing=listing,
        seller=seller,
        expires_at=timezone.now() + timedelta(seconds=UPLOAD_SESSION_LIFETIME_SECONDS),
        original_filename=original_filename[:255],
    )


def _read_upload(upload: Any) -> bytes:
    declared_size = getattr(upload, "size", 0)
    if declared_size > MAX_IMAGE_BYTES:
        raise ValidationError("Images must be 10 MB or smaller.")
    payload = cast(bytes, upload.read(MAX_IMAGE_BYTES + 1))
    if len(payload) > MAX_IMAGE_BYTES:
        raise ValidationError("Images must be 10 MB or smaller.")
    if not payload:
        raise ValidationError("Choose an image file.")
    return payload


def _processed_images(payload: bytes) -> tuple[bytes, bytes, int, int]:
    try:
        with Image.open(BytesIO(payload)) as source:
            source.verify()
        with Image.open(BytesIO(payload)) as source:
            if source.format not in ALLOWED_IMAGE_FORMATS:
                raise ValidationError("Only JPEG, PNG, and WebP images are accepted.")
            source.load()
            if source.width > MAX_IMAGE_DIMENSION or source.height > MAX_IMAGE_DIMENSION:
                raise ValidationError("Image dimensions are too large.")
            image = ImageOps.exif_transpose(source)
            if image.mode not in {"RGB", "L"}:
                background = Image.new("RGB", image.size, "white")
                if image.mode == "RGBA":
                    background.paste(image, mask=image.getchannel("A"))
                else:
                    background.paste(image.convert("RGB"))
                image = background
            else:
                image = image.convert("RGB")
            final = BytesIO()
            image.save(final, format="JPEG", quality=88, optimize=True)
            preview = image.copy()
            preview.thumbnail((640, 640))
            rendition = BytesIO()
            preview.save(rendition, format="JPEG", quality=82, optimize=True)
            return final.getvalue(), rendition.getvalue(), image.width, image.height
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValidationError("Choose a valid, safe image file.") from error


def finalize_image_upload(
    *, session_id: UUID, seller: SellerProfile, uploaded_file: Any
) -> ListingImage:
    expired = UploadSession.objects.filter(
        pk=session_id,
        seller=seller,
        state=UploadSessionState.OPEN,
        expires_at__lte=timezone.now(),
    ).update(state=UploadSessionState.EXPIRED)
    if expired:
        raise ValidationError("This upload session has expired.")
    return _finalize_image_upload(
        session_id=session_id,
        seller=seller,
        uploaded_file=uploaded_file,
    )


@transaction.atomic
def _finalize_image_upload(
    *, session_id: UUID, seller: SellerProfile, uploaded_file: Any
) -> ListingImage:
    session = (
        UploadSession.objects.select_for_update()
        .select_related("listing__category")
        .get(pk=session_id)
    )
    listing = _locked_owned_draft(listing_id=session.listing_id, seller=seller)
    previous = listing.status
    if session.seller_id != seller.id or session.state != UploadSessionState.OPEN:
        raise PermissionDenied("This upload session cannot be used.")
    if session.expires_at <= timezone.now():
        raise ValidationError("This upload session has expired.")
    _required_count, maximum_count = image_policy_for_listing(listing=listing)
    ready_images = ListingImage.objects.filter(listing=listing, state=ListingImageState.READY)
    if ready_images.count() >= maximum_count:
        raise ValidationError("This draft has reached its image limit.")
    payload = _read_upload(uploaded_file)
    final, rendition, width, height = _processed_images(payload)
    key_prefix = f"private-listings/{listing.id}/{session.id}"
    staged_key = f"staging/{session.id}"
    final_key = f"{key_prefix}/image.jpg"
    rendition_key = f"{key_prefix}/preview.jpg"
    default_storage.save(staged_key, ContentFile(payload))
    default_storage.save(final_key, ContentFile(final))
    default_storage.save(rendition_key, ContentFile(rendition))
    last_order = ready_images.aggregate(value=Max("ordering"))["value"]
    next_order = 0 if last_order is None else last_order + 1
    image = ListingImage.objects.create(
        listing=listing,
        upload_session=session,
        ordering=next_order,
        content_type="image/jpeg",
        byte_size=len(final),
        width=width,
        height=height,
        storage_key=final_key,
        rendition_key=rendition_key,
        original_filename=session.original_filename,
    )
    session.staged_key = staged_key
    session.state = UploadSessionState.FINALIZED
    session.finalized_at = timezone.now()
    session.save(update_fields=("staged_key", "state", "finalized_at"))
    default_storage.delete(staged_key)
    _depublish_material_edit(listing=listing, seller=seller, previous=previous)
    return image


@transaction.atomic
def reorder_images(*, listing_id: UUID, seller: SellerProfile, image_ids: list[UUID]) -> None:
    listing = _locked_owned_draft(listing_id=listing_id, seller=seller)
    previous = listing.status
    images = list(
        ListingImage.objects.select_for_update()
        .filter(listing=listing, state=ListingImageState.READY)
        .order_by("ordering")
    )
    if set(image_ids) != {image.id for image in images} or len(image_ids) != len(images):
        raise ValidationError("Use the complete image order for this draft.")
    for offset, image_id in enumerate(image_ids):
        ListingImage.objects.filter(pk=image_id).update(ordering=offset + len(images))
    for offset, image_id in enumerate(image_ids):
        ListingImage.objects.filter(pk=image_id).update(ordering=offset)
    _depublish_material_edit(listing=listing, seller=seller, previous=previous)


@transaction.atomic
def delete_listing_image(*, listing_id: UUID, image_id: UUID, seller: SellerProfile) -> None:
    listing = _locked_owned_draft(listing_id=listing_id, seller=seller)
    previous = listing.status
    image = ListingImage.objects.select_for_update().get(
        pk=image_id, listing=listing, state=ListingImageState.READY
    )
    image.state = ListingImageState.DELETED
    image.deleted_at = timezone.now()
    image.save(update_fields=("state", "deleted_at"))
    default_storage.delete(image.storage_key)
    default_storage.delete(image.rendition_key)
    for offset, remaining in enumerate(
        ListingImage.objects.filter(listing=listing, state=ListingImageState.READY).order_by(
            "ordering"
        )
    ):
        ListingImage.objects.filter(pk=remaining.pk).update(ordering=offset)
    _depublish_material_edit(listing=listing, seller=seller, previous=previous)


def _validated_video_payload(upload: Any) -> tuple[bytes, str]:
    declared_size = getattr(upload, "size", 0)
    if declared_size > MAX_VIDEO_BYTES:
        raise ValidationError("Videos must be 100 MB or smaller.")
    payload = cast(bytes, upload.read(MAX_VIDEO_BYTES + 1))
    if len(payload) > MAX_VIDEO_BYTES:
        raise ValidationError("Videos must be 100 MB or smaller.")
    if not payload:
        raise ValidationError("Choose a video file.")
    if len(payload) >= MP4_SIGNATURE_MINIMUM_BYTES and payload[4:8] == b"ftyp":
        return payload, "video/mp4"
    if (
        len(payload) >= WEBM_SIGNATURE_MINIMUM_BYTES
        and payload[:4] == b"\x1aE\xdf\xa3"
        and b"webm" in payload[:VIDEO_SIGNATURE_SCAN_BYTES].lower()
    ):
        return payload, "video/webm"
    raise ValidationError("Only valid MP4 and WebM videos are accepted.")


@transaction.atomic
def upload_listing_video(
    *, listing_id: UUID, seller: SellerProfile, uploaded_file: Any
) -> ListingVideo:
    """Store an untranscoded supplemental video under the owner lock."""
    if not settings.LISTING_MEDIA_ENABLED:
        raise ValidationError("Listing video uploads are not configured in this environment.")
    listing = _locked_owned_draft(listing_id=listing_id, seller=seller)
    previous = listing.status
    payload, content_type = _validated_video_payload(uploaded_file)
    video_id = uuid.uuid4()
    storage_key = f"private-listings/{listing.id}/videos/{video_id}/source"
    default_storage.save(storage_key, ContentFile(payload))
    video = ListingVideo.objects.create(
        id=video_id,
        listing=listing,
        content_type=content_type,
        byte_size=len(payload),
        storage_key=storage_key,
        original_filename=(getattr(uploaded_file, "name", "") or "")[:255],
    )
    _depublish_material_edit(listing=listing, seller=seller, previous=previous)
    return video


@transaction.atomic
def delete_listing_video(*, listing_id: UUID, video_id: UUID, seller: SellerProfile) -> None:
    listing = _locked_owned_draft(listing_id=listing_id, seller=seller)
    previous = listing.status
    video = ListingVideo.objects.select_for_update().get(
        pk=video_id, listing=listing, state=ListingVideoState.READY
    )
    video.state = ListingVideoState.DELETED
    video.deleted_at = timezone.now()
    video.save(update_fields=("state", "deleted_at"))
    default_storage.delete(video.storage_key)
    _depublish_material_edit(listing=listing, seller=seller, previous=previous)
