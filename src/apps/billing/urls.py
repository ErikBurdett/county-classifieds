from __future__ import annotations

from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("dashboard/listings/<uuid:listing_id>/checkout/", views.checkout, name="checkout"),
    path(
        "dashboard/listings/<uuid:listing_id>/renew/",
        views.renewal_checkout,
        name="renewal_checkout",
    ),
    path(
        "billing/orders/<uuid:order_id>/success/", views.checkout_success, name="checkout_success"
    ),
    path("billing/orders/<uuid:order_id>/cancel/", views.checkout_cancel, name="checkout_cancel"),
    path("staff/billing/reconciliation/", views.reconciliation, name="reconciliation"),
    path(
        "staff/billing/orders/<uuid:order_id>/local-confirm/",
        views.local_confirm,
        name="local_confirm",
    ),
]
