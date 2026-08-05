from __future__ import annotations

from uuid import UUID

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.models import SellerProfile

from .models import Order
from .selectors import reconciliation_orders
from .services import (
    BillingError,
    create_checkout_order,
    create_renewal_order,
    record_local_payment,
)


def _seller(request: HttpRequest) -> SellerProfile:
    return get_object_or_404(SellerProfile, user=request.user)


@login_required
def checkout(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    try:
        checkout_order = create_checkout_order(listing_id=listing_id, seller_id=_seller(request).id)
    except PermissionDenied:
        raise
    except (BillingError, ValidationError) as error:
        messages.error(request, "; ".join(error.messages))
        return redirect("listings:dashboard")
    return redirect("billing:checkout_success", order_id=checkout_order.order.id)


@login_required
def renewal_checkout(request: HttpRequest, listing_id: UUID) -> HttpResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    try:
        checkout_order = create_renewal_order(listing_id=listing_id, seller_id=_seller(request).id)
    except PermissionDenied:
        raise
    except (BillingError, ValidationError) as error:
        messages.error(request, "; ".join(error.messages))
        return redirect("listings:dashboard")
    return redirect("billing:checkout_success", order_id=checkout_order.order.id)


@login_required
def checkout_success(request: HttpRequest, order_id: UUID) -> HttpResponse:
    order = get_object_or_404(Order, pk=order_id, seller=_seller(request))
    return render(request, "billing/checkout_success.html", {"order": order})


@login_required
def checkout_cancel(request: HttpRequest, order_id: UUID) -> HttpResponse:
    order = get_object_or_404(Order, pk=order_id, seller=_seller(request))
    return render(request, "billing/checkout_cancel.html", {"order": order})


@login_required
def local_confirm(request: HttpRequest, order_id: UUID) -> HttpResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not settings.DEBUG or not request.user.has_perm("billing.change_order"):
        raise PermissionDenied
    get_object_or_404(Order, pk=order_id)
    record_local_payment(order_id=order_id)
    messages.success(request, "Local demo payment recorded. The approved listing is now published.")
    return redirect("billing:reconciliation")


@login_required
def reconciliation(request: HttpRequest) -> HttpResponse:
    if not request.user.has_perm("billing.view_order"):
        raise PermissionDenied
    return render(
        request,
        "billing/reconciliation.html",
        {"orders": reconciliation_orders(), "debug": settings.DEBUG},
    )
