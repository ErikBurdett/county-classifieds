from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_protect

from apps.accounts.models import SellerProfileRevision, SellerProfileRevisionStatus, User
from apps.accounts.services import review_seller_profile_revision
from apps.billing.models import OrderStatus

from .forms import StaffAuthenticationForm
from .selectors import management_dashboard, management_notifications


def _safe_next_url(request: HttpRequest, next_url: str | None) -> str:
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return reverse("management_console:dashboard")


def staff_required(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    @wraps(view)
    def wrapped(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        if request.user.is_authenticated and request.user.is_staff:
            return view(request, *args, **kwargs)
        if request.user.is_authenticated:
            logout(request)
            return redirect("management_console:login")
        return redirect(
            f"{reverse('management_console:login')}?{urlencode({'next': request.get_full_path()})}"
        )

    return wrapped


@csrf_protect
def staff_login(request: HttpRequest) -> HttpResponse:
    next_url = _safe_next_url(request, request.POST.get("next") or request.GET.get("next"))
    if request.user.is_authenticated and request.user.is_staff:
        return redirect(next_url)
    if request.method == "POST":
        # Ensure a denied non-staff attempt cannot retain an existing session.
        logout(request)
        form = StaffAuthenticationForm(request=request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect(next_url)
    else:
        form = StaffAuthenticationForm(request=request)
    return render(request, "management_console/login.html", {"form": form, "next": next_url})


@staff_required
def staff_logout(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return HttpResponse(status=405)
    logout(request)
    return redirect("management_console:login")


def _admin_changelist(model_name: str, **query: str) -> str:
    url = reverse(f"admin:{model_name}_changelist")
    return f"{url}?{urlencode(query)}" if query else url


def _operation_links(request: HttpRequest) -> list[dict[str, str]]:
    user = request.user
    links: list[dict[str, str]] = []
    if user.has_perm("listings.moderate_listing"):
        links.append(
            {
                "title": "Moderation queue",
                "detail": "Review assigned, unassigned, and escalated listings.",
                "url": reverse("listings:moderation_queue"),
            }
        )
    if user.has_perm("reports.triage_listingreport"):
        links.append(
            {
                "title": "Listing reports",
                "detail": "Review public listing reports and record triage actions.",
                "url": reverse("reports:queue"),
            }
        )
    if user.has_perm("accounts.change_sellerprofilerevision"):
        links.append(
            {
                "title": "Seller profile reviews",
                "detail": "Approve or reject submitted public profile revisions.",
                "url": reverse("management_console:profile_review_queue"),
            }
        )
    if user.has_perm("billing.view_order"):
        links.extend(
            (
                {
                    "title": "Billing reconciliation",
                    "detail": "Open the existing staff reconciliation workflow.",
                    "url": reverse("billing:reconciliation"),
                },
                {
                    "title": "Orders requiring review",
                    "detail": "Open a filtered, read-only order queue.",
                    "url": _admin_changelist(
                        "billing_order",
                        status__in=f"{OrderStatus.PENDING},{OrderStatus.PAYMENT_FAILED}",
                    ),
                },
            )
        )
    admin_links = (
        ("policies.view_policydocument", "Policy documents", "policies_policydocument"),
        ("catalog.view_category", "Catalog", "catalog_category"),
        ("locations.view_county", "Geography", "locations_county"),
        ("core.view_outboxevent", "Outbox operations", "core_outboxevent"),
    )
    for permission, title, model_name in admin_links:
        if user.has_perm(permission):
            links.append(
                {
                    "title": title,
                    "detail": f"Open {title.lower()} in Django admin.",
                    "url": _admin_changelist(model_name),
                }
            )
    return links


@staff_required
def dashboard(request: HttpRequest) -> HttpResponse:
    assert isinstance(request.user, User)
    return render(
        request,
        "management_console/dashboard.html",
        {
            "metrics": management_dashboard(),
            "operation_links": _operation_links(request),
            "management_notifications": management_notifications(user=request.user),
            "is_local_demo": settings.DEBUG,
        },
    )


@staff_required
def profile_review_queue(request: HttpRequest) -> HttpResponse:
    assert isinstance(request.user, User)
    if not request.user.has_perm("accounts.change_sellerprofilerevision"):
        raise PermissionDenied("You do not have permission to review seller profiles.")
    if request.method == "POST":
        revision = get_object_or_404(
            SellerProfileRevision,
            pk=request.POST.get("revision_id"),
            status=SellerProfileRevisionStatus.PENDING,
        )
        outcome = request.POST.get("outcome")
        status = {
            "approve": SellerProfileRevisionStatus.APPROVED,
            "reject": SellerProfileRevisionStatus.REJECTED,
        }.get(outcome or "")
        if status is None:
            messages.error(request, "Choose approve or reject.")
        else:
            review_seller_profile_revision(
                revision_id=revision.pk,
                reviewer=request.user,
                status=status,
                note=request.POST.get("review_note", "").strip(),
            )
            messages.success(request, "Seller profile revision reviewed.")
        return redirect("management_console:profile_review_queue")
    revisions = SellerProfileRevision.objects.filter(
        status=SellerProfileRevisionStatus.PENDING
    ).select_related("seller_profile__user")
    return render(
        request,
        "management_console/profile_review_queue.html",
        {"revisions": revisions},
    )
