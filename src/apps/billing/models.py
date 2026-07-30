from __future__ import annotations

import uuid

from django.core.validators import RegexValidator
from django.db import models


class OrderStatus(models.TextChoices):
    PENDING = "pending", "Pending payment"
    PAID = "paid", "Paid"
    PAYMENT_FAILED = "payment_failed", "Payment failed"
    REFUND_PENDING = "refund_pending", "Refund pending"
    REFUNDED = "refunded", "Refunded"


class OrderPurpose(models.TextChoices):
    NEW_LISTING = "new_listing", "New listing"
    RENEWAL = "renewal", "Renewal"


class PaymentEventStatus(models.TextChoices):
    RECEIVED = "received", "Received"
    PROCESSED = "processed", "Processed"
    IGNORED = "ignored", "Ignored"
    FAILED = "failed", "Failed"


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey("listings.Listing", on_delete=models.PROTECT, related_name="orders")
    seller = models.ForeignKey(
        "accounts.SellerProfile", on_delete=models.PROTECT, related_name="orders"
    )
    status = models.CharField(
        max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING
    )
    purpose = models.CharField(
        max_length=16, choices=OrderPurpose.choices, default=OrderPurpose.NEW_LISTING
    )
    currency = models.CharField(max_length=3, validators=[RegexValidator(r"^[A-Z]{3}$")])
    total_minor = models.PositiveBigIntegerField()
    provider = models.CharField(max_length=32, default="local_demo")
    provider_reference = models.CharField(max_length=128, unique=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total_minor__gte=0), name="billing_order_total_valid"
            ),
            models.UniqueConstraint(
                fields=("listing", "purpose"),
                condition=models.Q(status=OrderStatus.PENDING, purpose=OrderPurpose.RENEWAL),
                name="billing_one_pending_renewal",
            ),
            models.CheckConstraint(
                condition=models.Q(currency__regex=r"^[A-Z]{3}$"),
                name="billing_order_currency_iso",
            ),
        ]
        indexes = [
            models.Index(fields=("status", "created_at"), name="billing_order_reconcile_idx")
        ]

    def __str__(self) -> str:
        return f"Order {self.id}"


class OrderLine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="lines")
    product = models.ForeignKey(
        "catalog.ListingProduct", on_delete=models.PROTECT, related_name="order_lines"
    )
    product_code = models.CharField(max_length=64)
    description = models.CharField(max_length=200)
    unit_amount_minor = models.PositiveBigIntegerField()
    quantity = models.PositiveSmallIntegerField(default=1)
    currency = models.CharField(max_length=3, validators=[RegexValidator(r"^[A-Z]{3}$")])
    duration_days = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1), name="billing_line_quantity_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(duration_days__gte=1), name="billing_line_duration_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(currency__regex=r"^[A-Z]{3}$"),
                name="billing_line_currency_iso",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product_code} on {self.order_id}"


class PaymentEvent(models.Model):
    """Provider-neutral durable event; maps directly to a future StripeEvent."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=32)
    provider_event_id = models.CharField(max_length=128)
    event_type = models.CharField(max_length=64)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payment_events")
    amount_minor = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=3, validators=[RegexValidator(r"^[A-Z]{3}$")])
    occurred_at = models.DateTimeField()
    status = models.CharField(
        max_length=16, choices=PaymentEventStatus.choices, default=PaymentEventStatus.RECEIVED
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("provider", "provider_event_id"), name="billing_provider_event_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(currency__regex=r"^[A-Z]{3}$"),
                name="billing_event_currency_iso",
            ),
        ]
        indexes = [models.Index(fields=("status", "created_at"), name="billing_event_replay_idx")]

    def __str__(self) -> str:
        return f"{self.provider}:{self.provider_event_id}"


class FeaturedPlacement(models.Model):
    """Reserved entitlement primitive; browse exposure awaits DEC-107."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.PROTECT, related_name="featured_placements"
    )
    order_line = models.OneToOneField(
        OrderLine, on_delete=models.PROTECT, related_name="featured_placement"
    )
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Featured placement for {self.listing_id}"
