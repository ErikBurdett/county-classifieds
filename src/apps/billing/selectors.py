from __future__ import annotations

from django.db.models import QuerySet

from apps.accounts.models import SellerProfile

from .models import Order, PaymentEvent, PaymentEventStatus


def orders_for_seller(*, seller_id: int | SellerProfile) -> QuerySet[Order]:
    return (
        Order.objects.filter(seller_id=seller_id)
        .select_related("listing")
        .prefetch_related("lines")
    )


def reconciliation_orders() -> QuerySet[Order]:
    return (
        Order.objects.select_related("listing", "seller__user")
        .prefetch_related("payment_events")
        .order_by("-created_at")
    )


def replayable_events() -> QuerySet[PaymentEvent]:
    return PaymentEvent.objects.filter(
        status__in=(PaymentEventStatus.RECEIVED, PaymentEventStatus.FAILED)
    ).order_by("created_at")
