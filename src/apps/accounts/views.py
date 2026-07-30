from __future__ import annotations

from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from .forms import MarketplaceAuthenticationForm, SellerProfileForm, SellerRegistrationForm
from .models import AccountSecurityEventType, SellerProfile, User
from .services import record_security_event, register_seller


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
    try:
        profile = request.user.seller_profile
    except SellerProfile.DoesNotExist:
        profile = None

    if request.method == "POST":
        form = SellerProfileForm(request.POST, instance=profile)
        if form.is_valid():
            seller_profile = form.save(commit=False)
            seller_profile.user = request.user
            seller_profile.save()
            return redirect("listings:dashboard")
    else:
        form = SellerProfileForm(instance=profile)
    return render(request, "accounts/seller_profile_form.html", {"form": form})
