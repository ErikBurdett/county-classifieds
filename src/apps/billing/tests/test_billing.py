from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import SellerProfile, User
from apps.billing.models import OrderStatus, PaymentEvent, PaymentEventStatus
from apps.billing.selectors import orders_for_seller, reconciliation_orders, replayable_events
from apps.billing.services import (
    create_checkout_order,
    create_renewal_order,
    process_payment_event,
    record_local_payment,
)
from apps.catalog.models import (
    Category,
    ListingKind,
    ListingKindPriceMode,
    ListingPriceMode,
    ListingProduct,
    ListingProductUseCase,
    ProductPrice,
    Vertical,
)
from apps.listings.models import (
    AutoDetails,
    Listing,
    ListingStatus,
    ModerationActionType,
    ModerationReasonCode,
)
from apps.listings.services import moderate_listing, submit_listing
from apps.locations.models import County, State

pytestmark = pytest.mark.django_db


@pytest.fixture
def checkout_listing() -> tuple[Listing, SellerProfile, ListingProduct]:
    user = User.objects.create_user(email="seller@example.com", password="test-password")
    seller = SellerProfile.objects.create(user=user, display_name="Seller")
    vertical = Vertical.objects.create(name="Autos", slug="autos")
    category = Category.objects.create(vertical=vertical, name="Cars", slug="cars")
    state = State.objects.create(
        fips="48", usps_code="TX", name="Texas", slug="texas", is_active=True
    )
    county = County.objects.create(
        fips="48375", state=state, name="Potter", slug="potter", is_active=True
    )
    kind = ListingKind.objects.create(vertical=vertical, name="Automobile")
    ListingKindPriceMode.objects.create(listing_kind=kind, price_mode=ListingPriceMode.FIXED)
    product = ListingProduct.objects.create(
        listing_kind=kind,
        product_code="AUTOS_NEW_FIXED",
        use_case=ListingProductUseCase.NEW_LISTING,
        price_mode=ListingPriceMode.FIXED,
        duration_days=30,
    )
    ProductPrice.objects.create(
        product=product, currency="USD", amount_minor=1000, effective_from=timezone.now()
    )
    for product_code, amount_minor in (
        ("GENERIC_PRIMARY_PLACEMENT", 1000),
        ("GENERIC_ADDITIONAL_COUNTY", 500),
    ):
        distribution_product = ListingProduct.objects.create(
            product_code=product_code,
            use_case=ListingProductUseCase.NEW_LISTING,
            price_mode=ListingPriceMode.FIXED,
            is_generic_distribution=True,
            duration_days=30,
        )
        ProductPrice.objects.create(
            product=distribution_product,
            currency="USD",
            amount_minor=amount_minor,
            effective_from=timezone.now(),
        )
    listing = Listing.objects.create(
        seller=seller,
        vertical=vertical,
        category=category,
        listing_kind=kind,
        state=state,
        county=county,
        city="Amarillo",
        title="Demo car",
        description="Demo listing",
        price_minor=2500000,
        currency="USD",
        status=ListingStatus.AWAITING_PAYMENT,
    )
    return listing, seller, product


def test_checkout_snapshots_server_owned_price(
    checkout_listing: tuple[Listing, SellerProfile, ListingProduct],
) -> None:
    listing, seller, _product = checkout_listing

    checkout = create_checkout_order(listing_id=listing.id, seller_id=seller.id)

    assert checkout.order.total_minor == 1000
    assert checkout.order.currency == "USD"
    assert checkout.order.lines.get().product_code == "GENERIC_PRIMARY_PLACEMENT"
    assert checkout.order.lines.get().duration_days == 30


def test_checkout_rejects_wrong_owner(
    checkout_listing: tuple[Listing, SellerProfile, ListingProduct],
) -> None:
    listing, _seller, _product = checkout_listing
    other = SellerProfile.objects.create(
        user=User.objects.create_user(email="other@example.com", password="test-password"),
        display_name="Other",
    )

    with pytest.raises(PermissionDenied):
        create_checkout_order(listing_id=listing.id, seller_id=other.id)


def test_payment_event_mismatch_and_duplicate_are_safe(
    checkout_listing: tuple[Listing, SellerProfile, ListingProduct],
) -> None:
    listing, seller, _product = checkout_listing
    order = create_checkout_order(listing_id=listing.id, seller_id=seller.id).order
    bad = PaymentEvent.objects.create(
        provider="local_demo",
        provider_event_id="bad",
        event_type="checkout.payment_succeeded",
        order=order,
        amount_minor=999,
        currency="USD",
        occurred_at=timezone.now(),
    )

    assert process_payment_event(event_id=bad.id).status == PaymentEventStatus.FAILED
    event = record_local_payment(order_id=order.id)
    event.refresh_from_db()
    order.refresh_from_db()
    listing.refresh_from_db()
    assert event.status == PaymentEventStatus.PROCESSED
    assert order.status == OrderStatus.PAID
    assert listing.status == ListingStatus.PUBLISHED
    assert record_local_payment(order_id=order.id).id == event.id


def test_browser_success_page_never_marks_paid(
    client: Client, checkout_listing: tuple[Listing, SellerProfile, ListingProduct]
) -> None:
    listing, seller, _product = checkout_listing
    order = create_checkout_order(listing_id=listing.id, seller_id=seller.id).order
    client.force_login(seller.user)

    response = client.get(reverse("billing:checkout_success", kwargs={"order_id": order.id}))

    order.refresh_from_db()
    assert response.status_code == 200
    assert order.status == OrderStatus.PENDING


def test_local_confirm_requires_debug_staff(
    client: Client, checkout_listing: tuple[Listing, SellerProfile, ListingProduct]
) -> None:
    listing, seller, _product = checkout_listing
    order = create_checkout_order(listing_id=listing.id, seller_id=seller.id).order
    client.force_login(seller.user)
    url = reverse("billing:local_confirm", kwargs={"order_id": order.id})
    assert client.post(url).status_code == 403

    seller.user.is_staff = True
    seller.user.save(update_fields=("is_staff",))
    seller.user.user_permissions.add(
        Permission.objects.get(content_type__app_label="billing", codename="change_order")
    )
    with override_settings(DEBUG=True):
        assert client.post(url).status_code == 302
    order.refresh_from_db()
    assert order.status == OrderStatus.PAID


def test_catalog_price_window_is_required(
    checkout_listing: tuple[Listing, SellerProfile, ListingProduct],
) -> None:
    listing, seller, _product = checkout_listing
    ProductPrice.objects.filter(product__product_code="GENERIC_PRIMARY_PLACEMENT").delete()

    with pytest.raises(Exception, match="local-demo quote is not configured"):
        create_checkout_order(listing_id=listing.id, seller_id=seller.id)


def test_submission_always_enters_review(
    checkout_listing: tuple[Listing, SellerProfile, ListingProduct],
) -> None:
    listing, seller, _product = checkout_listing
    AutoDetails.objects.create(
        listing=listing,
        vehicle_type="car",
        year=2020,
        make="Ford",
        model="Mustang",
        mileage=12000,
        title_status="clean",
        vin="1HGCM82633A004352",
    )
    listing.status = ListingStatus.DRAFT
    listing.save(update_fields=("status",))

    with override_settings(DEBUG=True):
        submitted = submit_listing(listing_id=listing.id, seller=seller)

    assert submitted.status == ListingStatus.IN_REVIEW
    assert submitted.published_at is None


def test_checkout_post_and_cancel_are_owner_scoped(
    client: Client, checkout_listing: tuple[Listing, SellerProfile, ListingProduct]
) -> None:
    listing, seller, _product = checkout_listing
    client.force_login(seller.user)

    response = client.post(reverse("billing:checkout", kwargs={"listing_id": listing.id}))

    assert response.status_code == 302
    order = orders_for_seller(seller_id=seller.id).get()
    assert (
        client.get(reverse("billing:checkout_cancel", kwargs={"order_id": order.id})).status_code
        == 200
    )
    other = SellerProfile.objects.create(
        user=User.objects.create_user(email="other@example.com", password="test-password"),
        display_name="Other",
    )
    client.force_login(other.user)
    assert (
        client.get(reverse("billing:checkout_success", kwargs={"order_id": order.id})).status_code
        == 404
    )


def test_unchanged_grace_renewal_is_idempotent_and_restores_expiry(
    checkout_listing: tuple[Listing, SellerProfile, ListingProduct],
) -> None:
    listing, seller, product = checkout_listing
    renewal_product = ListingProduct.objects.create(
        listing_kind=product.listing_kind,
        product_code="AUTOS_RENEW_FIXED",
        use_case=ListingProductUseCase.RENEWAL,
        price_mode=ListingPriceMode.FIXED,
        duration_days=14,
    )
    ProductPrice.objects.create(
        product=renewal_product, currency="USD", amount_minor=1000, effective_from=timezone.now()
    )
    listing.status = ListingStatus.EXPIRED
    listing.expires_at = timezone.now() - timedelta(days=1)
    listing.save(update_fields=("status", "expires_at"))

    first = create_renewal_order(listing_id=listing.id, seller_id=seller.id)
    second = create_renewal_order(listing_id=listing.id, seller_id=seller.id)
    record_local_payment(order_id=first.order.id)
    listing.refresh_from_db()

    assert first.order.id == second.order.id
    assert listing.status == ListingStatus.PUBLISHED
    assert listing.expires_at is not None
    assert listing.expires_at > timezone.now() + timedelta(days=13)


def test_renewal_outside_grace_fails_closed(
    checkout_listing: tuple[Listing, SellerProfile, ListingProduct],
) -> None:
    listing, seller, _product = checkout_listing
    listing.status = ListingStatus.EXPIRED
    listing.expires_at = timezone.now() - timedelta(days=8)
    listing.save(update_fields=("status", "expires_at"))

    with pytest.raises(Exception, match="requires a new moderated submission"):
        create_renewal_order(listing_id=listing.id, seller_id=seller.id)


def test_staff_reconciliation_and_replay_command(
    client: Client, checkout_listing: tuple[Listing, SellerProfile, ListingProduct]
) -> None:
    listing, seller, _product = checkout_listing
    order = create_checkout_order(listing_id=listing.id, seller_id=seller.id).order
    event = PaymentEvent.objects.create(
        provider="local_demo",
        provider_event_id="replay-me",
        event_type="checkout.payment_succeeded",
        order=order,
        amount_minor=order.total_minor,
        currency=order.currency,
        occurred_at=timezone.now(),
    )
    seller.user.is_staff = True
    seller.user.save(update_fields=("is_staff",))
    seller.user.user_permissions.add(
        Permission.objects.get(content_type__app_label="billing", codename="view_order")
    )
    client.force_login(seller.user)

    assert client.get(reverse("billing:reconciliation")).status_code == 200
    assert reconciliation_orders().count() == 1
    assert replayable_events().count() == 1
    call_command("replay_payment_events")
    event.refresh_from_db()
    assert event.status == PaymentEventStatus.PROCESSED


def test_rejection_refunds_paid_local_order_once(
    checkout_listing: tuple[Listing, SellerProfile, ListingProduct],
) -> None:
    listing, seller, _product = checkout_listing
    order = create_checkout_order(listing_id=listing.id, seller_id=seller.id).order
    record_local_payment(order_id=order.id)
    listing.refresh_from_db()
    moderator = User.objects.create_user(email="moderator@example.com", password="test-password")
    moderator.user_permissions.add(
        Permission.objects.get(content_type__app_label="listings", codename="moderate_listing")
    )
    reason = ModerationReasonCode.objects.create(
        code="reject_test", category="Test", seller_facing_text="Rejected"
    )

    moderate_listing(
        listing_id=listing.id,
        actor=moderator,
        revision=listing.lifecycle_revision,
        outcome=ModerationActionType.REJECTED,
        reason_code=reason,
    )

    order.refresh_from_db()
    refund = PaymentEvent.objects.get(event_type="charge.refunded")
    assert order.status == OrderStatus.REFUNDED
    assert refund.status == PaymentEventStatus.PROCESSED
    assert refund.amount_minor == order.total_minor


def test_demo_seed_is_debug_only_and_idempotent(
    checkout_listing: tuple[Listing, SellerProfile, ListingProduct],
) -> None:
    _listing, _seller, product = checkout_listing
    with pytest.raises(CommandError):
        call_command("seed_demo_billing")

    with override_settings(DEBUG=True):
        call_command("seed_demo_billing")
        call_command("seed_demo_billing")
    assert (
        ProductPrice.objects.filter(
            product=product, currency="USD", amount_minor=1000, effective_until__isnull=True
        ).count()
        == 1
    )
