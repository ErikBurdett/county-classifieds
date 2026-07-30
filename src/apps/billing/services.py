from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.utils import timezone

from apps.accounts.services import require_active_account
from apps.catalog.models import (
    ListingPriceMode,
    ListingProduct,
    ListingProductUseCase,
    ProductPrice,
)
from apps.catalog.services import ProductSelection, resolve_eligible_product_price
from apps.core.outbox import enqueue_event
from apps.listings.models import Listing, ListingStatus, ModerationAction, ModerationActionType

from .models import Order, OrderLine, OrderPurpose, OrderStatus, PaymentEvent, PaymentEventStatus

LOCAL_PROVIDER = "local_demo"
LOCAL_EVENT_TYPE = "checkout.payment_succeeded"
LOCAL_REFUND_EVENT_TYPE = "charge.refunded"
GENERIC_PRIMARY_PRODUCT_CODE = "GENERIC_PRIMARY_PLACEMENT"
GENERIC_ADDITIONAL_PRODUCT_CODE = "GENERIC_ADDITIONAL_COUNTY"


class BillingError(ValidationError):
    """A safe, user-actionable billing boundary failure."""


@dataclass(frozen=True)
class CheckoutOrder:
    order: Order
    created: bool


def _generic_price(*, product_code: str) -> tuple[ListingProduct, ProductPrice]:
    now = timezone.now()
    product = ListingProduct.objects.get(
        product_code=product_code, is_active=True, is_generic_distribution=True
    )
    price = (
        product.prices.filter(
            currency="USD",
            effective_from__lte=now,
        )
        .filter(models.Q(effective_until__isnull=True) | models.Q(effective_until__gt=now))
        .order_by("-effective_from")
        .first()
    )
    if price is None:
        raise BillingError("The generic local-demo quote is not configured.")
    return product, price


@transaction.atomic
def create_generic_distribution_quote(*, listing_id: UUID, seller_id: int) -> CheckoutOrder:
    """Snapshot the $10/$5 local-demo placement quote; it never grants payment state."""

    listing = (
        Listing.objects.select_for_update()
        .select_related("seller__user", "generic_details")
        .prefetch_related("additional_counties")
        .get(pk=listing_id)
    )
    if listing.seller_id != seller_id:
        raise PermissionDenied("Only the listing owner may create a quote.")
    require_active_account(user=listing.seller.user)
    if not hasattr(listing, "generic_details"):
        raise BillingError("This listing is not a generic listing.")
    existing = Order.objects.filter(
        listing=listing,
        seller_id=seller_id,
        purpose=OrderPurpose.NEW_LISTING,
        provider=LOCAL_PROVIDER,
    ).first()
    if existing is not None:
        return CheckoutOrder(order=existing, created=False)
    primary_product, primary_price = _generic_price(product_code=GENERIC_PRIMARY_PRODUCT_CODE)
    additional_product, additional_price = _generic_price(
        product_code=GENERIC_ADDITIONAL_PRODUCT_CODE
    )
    additional_count = listing.additional_counties.count()
    total = primary_price.amount_minor + additional_price.amount_minor * additional_count
    order = Order.objects.create(
        listing=listing,
        seller_id=seller_id,
        currency="USD",
        total_minor=total,
        provider=LOCAL_PROVIDER,
        provider_reference=f"local-generic-quote-{uuid4()}",
    )
    OrderLine.objects.create(
        order=order,
        product=primary_product,
        product_code=primary_product.product_code,
        description="Generic listing primary county placement (local demo)",
        unit_amount_minor=primary_price.amount_minor,
        currency="USD",
        quantity=1,
        duration_days=primary_product.duration_days or 30,
    )
    if additional_count:
        OrderLine.objects.create(
            order=order,
            product=additional_product,
            product_code=additional_product.product_code,
            description="Generic listing additional county placement (local demo)",
            unit_amount_minor=additional_price.amount_minor,
            currency="USD",
            quantity=additional_count,
            duration_days=additional_product.duration_days or 30,
        )
    return CheckoutOrder(order=order, created=True)


def _selection_for_listing(
    *, listing: Listing, use_case: ListingProductUseCase = ListingProductUseCase.NEW_LISTING
) -> ProductSelection:
    if (
        listing.listing_kind is None
        or listing.vertical.slug != "autos"
        or listing.price_minor is None
    ):
        raise BillingError("This listing is not eligible for the local billing demo.")
    product = ListingProduct.objects.filter(
        listing_kind=listing.listing_kind,
        use_case=use_case,
        price_mode=ListingPriceMode.FIXED,
        is_active=True,
    ).first()
    if product is None:
        raise BillingError("No active server-priced product is available for this request.")
    return ProductSelection(
        listing_kind=listing.listing_kind,
        product_code=product.product_code,
        use_case=use_case,
        price_mode=ListingPriceMode.FIXED,
    )


@transaction.atomic
def create_checkout_order(
    *, listing_id: UUID, seller_id: int, purpose: OrderPurpose = OrderPurpose.NEW_LISTING
) -> CheckoutOrder:
    """Create one immutable local-demo order from server-resolved catalog data."""
    listing = (
        Listing.objects.select_for_update()
        .select_related("seller__user", "listing_kind", "vertical")
        .get(pk=listing_id)
    )
    if listing.seller_id != seller_id:
        raise PermissionDenied("Only the listing owner may start checkout.")
    require_active_account(user=listing.seller.user)
    allowed_status = (
        {ListingStatus.AWAITING_PAYMENT}
        if purpose == OrderPurpose.NEW_LISTING
        else {ListingStatus.EXPIRED, ListingStatus.PUBLISHED}
    )
    if listing.status not in allowed_status:
        raise BillingError("This listing is not eligible for checkout.")
    existing = Order.objects.filter(
        listing=listing,
        seller_id=seller_id,
        status=OrderStatus.PENDING,
        provider=LOCAL_PROVIDER,
        purpose=purpose,
    ).first()
    if existing is not None:
        return CheckoutOrder(order=existing, created=False)
    resolved = resolve_eligible_product_price(
        selection=_selection_for_listing(
            listing=listing,
            use_case=(
                ListingProductUseCase.RENEWAL
                if purpose == OrderPurpose.RENEWAL
                else ListingProductUseCase.NEW_LISTING
            ),
        ),
        currency="USD",
        at=timezone.now(),
    )
    duration_days = resolved.product.duration_days
    if duration_days is None:
        raise BillingError("The configured product has no listing duration.")
    order = Order.objects.create(
        listing=listing,
        seller_id=seller_id,
        currency=resolved.price.currency,
        total_minor=resolved.price.amount_minor,
        provider=LOCAL_PROVIDER,
        provider_reference=f"local-order-{uuid4()}",
        purpose=purpose,
    )
    OrderLine.objects.create(
        order=order,
        product=resolved.product,
        product_code=resolved.product.product_code,
        description="Autos new fixed-price listing",
        unit_amount_minor=resolved.price.amount_minor,
        quantity=1,
        currency=resolved.price.currency,
        duration_days=duration_days,
    )
    return CheckoutOrder(order=order, created=True)


def create_renewal_order(*, listing_id: UUID, seller_id: int) -> CheckoutOrder:
    """Create one pending renewal order within the accepted seven-day grace window."""
    listing = Listing.objects.filter(pk=listing_id, seller_id=seller_id).first()
    if listing is None:
        raise PermissionDenied("Only the listing owner may renew this listing.")
    if (
        listing.expires_at is None
        or listing.expires_at + timedelta(days=7) < timezone.now()
        or listing.last_material_edit_at is not None
    ):
        raise BillingError("This listing requires a new moderated submission.")
    return create_checkout_order(
        listing_id=listing_id, seller_id=seller_id, purpose=OrderPurpose.RENEWAL
    )


@transaction.atomic
def process_payment_event(*, event_id: UUID) -> PaymentEvent:
    """Process one durable event safely under replay, duplicates, and disorder."""
    event = (
        PaymentEvent.objects.select_for_update().select_related("order__listing").get(pk=event_id)
    )
    if event.status in {PaymentEventStatus.PROCESSED, PaymentEventStatus.IGNORED}:
        return event
    order = Order.objects.select_for_update().get(pk=event.order_id)
    if event.event_type == LOCAL_REFUND_EVENT_TYPE:
        if event.amount_minor != order.total_minor or event.currency != order.currency:
            event.status = PaymentEventStatus.FAILED
            event.failure_reason = (
                "Provider refund amount or currency did not match order snapshot."
            )
        elif order.status in {
            OrderStatus.REFUNDED,
            OrderStatus.PENDING,
            OrderStatus.PAYMENT_FAILED,
        }:
            event.status = PaymentEventStatus.IGNORED
        else:
            order.status = OrderStatus.REFUNDED
            order.save(update_fields=("status", "updated_at"))
            event.status = PaymentEventStatus.PROCESSED
    elif event.event_type != LOCAL_EVENT_TYPE:
        event.status = PaymentEventStatus.IGNORED
    elif event.amount_minor != order.total_minor or event.currency != order.currency:
        event.status = PaymentEventStatus.FAILED
        event.failure_reason = "Provider payment amount or currency did not match order snapshot."
    elif order.status != OrderStatus.PENDING:
        event.status = PaymentEventStatus.IGNORED
    else:
        listing = Listing.objects.select_for_update().get(pk=order.listing_id)
        if order.purpose == OrderPurpose.RENEWAL:
            _apply_paid_renewal(listing=listing, order=order)
            order.status = OrderStatus.PAID
            order.paid_at = timezone.now()
            order.save(update_fields=("status", "paid_at", "updated_at"))
            event.status = PaymentEventStatus.PROCESSED
        elif listing.status != ListingStatus.AWAITING_PAYMENT:
            event.status = PaymentEventStatus.FAILED
            event.failure_reason = "Listing is not awaiting payment."
        else:
            now = timezone.now()
            order.status = OrderStatus.PAID
            order.paid_at = now
            order.save(update_fields=("status", "paid_at", "updated_at"))
            previous = listing.status
            listing.status = ListingStatus.IN_REVIEW
            listing.lifecycle_revision += 1
            listing.save(update_fields=("status", "lifecycle_revision", "updated_at"))
            ModerationAction.objects.create(
                listing=listing,
                actor=None,
                action_type=ModerationActionType.SUBMITTED,
                from_status=previous,
                to_status=ListingStatus.IN_REVIEW,
            )
            event.status = PaymentEventStatus.PROCESSED
    event.processed_at = timezone.now()
    event.save(update_fields=("status", "failure_reason", "processed_at"))
    return event


def _apply_paid_renewal(*, listing: Listing, order: Order) -> None:
    """Restore visibility once, using the immutable duration snapshot."""
    if listing.expires_at is None:
        raise BillingError("A renewal requires an existing expiration.")
    line = order.lines.get()
    renewal_time = timezone.now()
    if (
        listing.expires_at + timedelta(days=7) < renewal_time
        or listing.last_material_edit_at is not None
    ):
        raise BillingError("This renewal no longer qualifies for immediate publication.")
    previous = listing.status
    listing.status = ListingStatus.PUBLISHED
    listing.published_at = renewal_time
    listing.expires_at = renewal_time + timedelta(days=line.duration_days)
    listing.lifecycle_revision += 1
    listing.save(
        update_fields=("status", "published_at", "expires_at", "lifecycle_revision", "updated_at")
    )
    ModerationAction.objects.create(
        listing=listing,
        actor=None,
        action_type=ModerationActionType.RENEWED,
        from_status=previous,
        to_status=ListingStatus.PUBLISHED,
    )
    enqueue_event(
        event_type="listing.approved",
        payload={"listing_id": str(listing.id), "seller_message": "Your renewal is active."},
        aggregate_type="listing",
        aggregate_reference=str(listing.id),
        idempotency_key=f"listing.approved:{listing.id}:{listing.lifecycle_revision}",
    )


@transaction.atomic
def record_local_payment(*, order_id: UUID) -> PaymentEvent:
    """Create/retrieve a deterministic local event, then process it."""
    order = Order.objects.select_for_update().get(pk=order_id)
    event, _created = PaymentEvent.objects.get_or_create(
        provider=LOCAL_PROVIDER,
        provider_event_id=f"local-payment-{order.id}",
        defaults={
            "event_type": LOCAL_EVENT_TYPE,
            "order": order,
            "amount_minor": order.total_minor,
            "currency": order.currency,
            "occurred_at": timezone.now(),
        },
    )
    return process_payment_event(event_id=event.id)


@transaction.atomic
def refund_rejected_listing(*, listing_id: UUID) -> list[PaymentEvent]:
    """Create one auditable full local refund per paid order; safe on retries and disorder."""
    orders = Order.objects.select_for_update().filter(
        listing_id=listing_id, provider=LOCAL_PROVIDER, status=OrderStatus.PAID
    )
    events: list[PaymentEvent] = []
    for order in orders:
        event, _created = PaymentEvent.objects.get_or_create(
            provider=LOCAL_PROVIDER,
            provider_event_id=f"local-refund-rejected-{order.id}",
            defaults={
                "event_type": LOCAL_REFUND_EVENT_TYPE,
                "order": order,
                "amount_minor": order.total_minor,
                "currency": order.currency,
                "occurred_at": timezone.now(),
            },
        )
        events.append(process_payment_event(event_id=event.id))
    return events
