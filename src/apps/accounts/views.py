from __future__ import annotations

import mimetypes
from uuid import UUID

from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from apps.listings.models import Listing, ListingStatus
from apps.listings.presenters import present_public_listing
from apps.listings.selectors import public_seller_feed_listings

from .forms import MarketplaceAuthenticationForm, SellerProfileForm, SellerRegistrationForm
from .models import (
    AccountSecurityEventType,
    SellerProfile,
    SellerProfileRevision,
    SellerProfileRevisionStatus,
    User,
)
from .selectors import public_seller_profile
from .services import record_security_event, register_seller, submit_seller_profile_revision


class MarketplaceLoginView(auth_views.LoginView):
    authentication_form = MarketplaceAuthenticationForm
    template_name = "accounts/login.html"

    def form_valid(self, form: AuthenticationForm) -> HttpResponse:
        response = super().form_valid(form)
        record_security_event(
            event_type=AccountSecurityEventType.LOGIN_SUCCEEDED,
            subject=form.get_user(),
            request=self.request,
        )
        return response

    def form_invalid(self, form: AuthenticationForm) -> HttpResponse:
        email = str(self.request.POST.get("username", "")).strip()
        subject = User.objects.filter(email__iexact=email).first() if email else None
        record_security_event(
            event_type=AccountSecurityEventType.LOGIN_FAILED, subject=subject, request=self.request
        )
        return super().form_invalid(form)


class MarketplacePasswordResetView(auth_views.PasswordResetView):
    template_name = "accounts/password_reset_form.html"
    email_template_name = "accounts/email/password_reset_email.txt"
    subject_template_name = "accounts/email/password_reset_subject.txt"
    success_url = "/password-reset/done/"

    def form_valid(self, form: PasswordResetForm) -> HttpResponse:
        email = str(form.cleaned_data["email"]).strip()
        subject = User.objects.filter(email__iexact=email, is_active=True).first()
        record_security_event(
            event_type=AccountSecurityEventType.PASSWORD_RESET_REQUESTED,
            subject=subject,
            request=self.request,
        )
        return super().form_valid(form)


class MarketplacePasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = "/password-reset/complete/"

    def form_valid(self, form: object) -> HttpResponse:
        response = super().form_valid(form)
        subject = self.user
        if isinstance(subject, User):
            record_security_event(
                event_type=AccountSecurityEventType.PASSWORD_RESET_COMPLETED,
                subject=subject,
                request=self.request,
            )
        return response


def register(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("listings:dashboard")

    if request.method == "POST":
        form = SellerRegistrationForm(request.POST)
        if form.is_valid():
            user = register_seller(
                email=form.cleaned_data["email"],
                display_name=form.cleaned_data["display_name"],
                password=form.cleaned_data["password1"],
            )
            record_security_event(
                event_type=AccountSecurityEventType.REGISTERED, subject=user, request=request
            )
            login(request, user)
            return redirect("listings:dashboard")
    else:
        form = SellerRegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


@login_required
def seller_profile(request: HttpRequest) -> HttpResponse:
    assert isinstance(request.user, User)
    profile = (
        SellerProfile.objects.select_related("current_approved_revision")
        .filter(user=request.user)
        .first()
    )
    approved_revision = profile.current_approved_revision if profile is not None else None

    if request.method == "POST":
        form = SellerProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            submit_seller_profile_revision(
                user=request.user,
                display_name=form.cleaned_data["display_name"],
                phone=form.cleaned_data["phone"],
                content=form.revision_content(),
                avatar=form.cleaned_data["avatar"],
            )
            return redirect("listings:dashboard")
    else:
        initial = (
            {
                field_name: getattr(approved_revision, field_name)
                for field_name in SellerProfileRevision.public_content_field_names()
            }
            if approved_revision is not None
            else None
        )
        form = SellerProfileForm(instance=profile, initial=initial)
    return render(
        request,
        "accounts/seller_profile_form.html",
        {"form": form, "approved_revision": approved_revision},
    )


@require_GET
def public_seller_profile_view(request: HttpRequest, public_id: UUID) -> HttpResponse:
    """Render a public seller page from safe, approved profile and listing data only."""
    seller = public_seller_profile(public_id=public_id)
    if seller is None:
        raise Http404("Seller not found.")
    feed = public_seller_feed_listings(seller=seller)
    page = Paginator(feed, 24).get_page(request.GET.get("page"))
    public_history = Listing.objects.filter(seller=seller, first_published_at__isnull=False)
    profile_listings = list(page.object_list)
    return render(
        request,
        "accounts/public_seller_profile.html",
        {
            "seller": seller,
            "revision": seller.current_approved_revision,
            "page_obj": page,
            "listing_cards": [
                {
                    "listing": listing,
                    "presentation": present_public_listing(listing=listing),
                    "image": next(iter(listing.images.all()), None),
                }
                for listing in profile_listings
            ],
            "states": sorted({listing.state for listing in feed}, key=lambda state: state.name),
            "counties": sorted(
                {listing.county for listing in feed},
                key=lambda county: (county.state.name, county.name),
            ),
            "public_listing_count": public_history.count(),
            "expired_count": public_history.filter(status=ListingStatus.EXPIRED).count(),
            "archived_count": public_history.filter(status=ListingStatus.ARCHIVED).count(),
        },
    )


@require_GET
def public_seller_avatar(request: HttpRequest, public_id: UUID) -> FileResponse:
    """Serve only the avatar included in a seller's current approved revision."""
    del request
    seller = public_seller_profile(public_id=public_id)
    if (
        seller is None
        or seller.current_approved_revision is None
        or seller.current_approved_revision.status != SellerProfileRevisionStatus.APPROVED
    ):
        raise Http404("Profile image not found.")
    avatar = seller.current_approved_revision.avatar
    if not avatar or not default_storage.exists(avatar.name):
        raise Http404("Profile image not found.")
    content_type = mimetypes.guess_type(avatar.name)[0] or "application/octet-stream"
    response = FileResponse(default_storage.open(avatar.name, "rb"), content_type=content_type)
    response["Cache-Control"] = "public, max-age=3600"
    response["Content-Disposition"] = "inline"
    return response
