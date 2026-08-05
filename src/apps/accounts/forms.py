from __future__ import annotations

from typing import ClassVar

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserChangeForm, UserCreationForm
from django.core.validators import URLValidator

from .managers import UserManager
from .models import SellerProfile, SellerProfileRevision, User


class MarketplaceAuthenticationForm(AuthenticationForm):
    """Use Django's generic failure message for inactive and unknown accounts."""

    def confirm_login_allowed(self, user: User) -> None:
        super().confirm_login_allowed(user)


class MarketplaceUserCreationForm(UserCreationForm):  # type: ignore[type-arg]
    class Meta:
        model = User
        fields = ("email",)

    def clean_email(self) -> str:
        return UserManager.normalize_marketplace_email(str(self.cleaned_data["email"]))


class SellerRegistrationForm(UserCreationForm):  # type: ignore[type-arg]
    display_name = forms.CharField(max_length=120)

    class Meta:
        model = User
        fields = ("email", "display_name")

    def clean_email(self) -> str:
        email = UserManager.normalize_marketplace_email(str(self.cleaned_data["email"]))
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_display_name(self) -> str:
        display_name = " ".join(str(self.cleaned_data["display_name"]).split())
        if SellerProfile.objects.filter(display_name__iexact=display_name).exists():
            raise forms.ValidationError("This display name is already in use.")
        return display_name


class MarketplaceUserChangeForm(UserChangeForm):  # type: ignore[type-arg]
    class Meta:
        model = User
        fields = "__all__"

    def clean_email(self) -> str:
        return UserManager.normalize_marketplace_email(str(self.cleaned_data["email"]))


class SellerProfileForm(forms.ModelForm):  # type: ignore[type-arg]
    avatar = forms.ImageField(
        required=False,
        help_text="JPEG, PNG, or WebP, up to 10 MB. Public only after staff approval.",
    )
    bio = forms.CharField(
        max_length=2_000,
        required=False,
        widget=forms.Textarea(attrs={"rows": 5}),
        help_text="This will be publicly visible only after staff approval.",
    )
    website_url = forms.URLField(
        required=False, assume_scheme="https", validators=[URLValidator(schemes=["https"])]
    )
    facebook_url = forms.URLField(
        required=False, assume_scheme="https", validators=[URLValidator(schemes=["https"])]
    )
    instagram_url = forms.URLField(
        required=False, assume_scheme="https", validators=[URLValidator(schemes=["https"])]
    )
    x_url = forms.URLField(
        required=False, assume_scheme="https", validators=[URLValidator(schemes=["https"])]
    )
    linkedin_url = forms.URLField(
        required=False, assume_scheme="https", validators=[URLValidator(schemes=["https"])]
    )
    youtube_url = forms.URLField(
        required=False, assume_scheme="https", validators=[URLValidator(schemes=["https"])]
    )

    class Meta:
        model = SellerProfile
        fields = ("display_name", "phone")
        help_texts: ClassVar[dict[str, str]] = {
            "phone": (
                "Optional. A phone number remains unverified until a future verification flow."
            ),
        }

    def revision_content(self) -> dict[str, str]:
        return {
            field_name: str(self.cleaned_data[field_name])
            for field_name in SellerProfileRevision.public_content_field_names()
        }

    def clean_avatar(self) -> object:
        avatar = self.cleaned_data.get("avatar")
        if avatar is None:
            return avatar
        if avatar.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Profile images must be 10 MB or smaller.")
        if getattr(avatar, "content_type", "") not in {"image/jpeg", "image/png", "image/webp"}:
            raise forms.ValidationError("Upload a JPEG, PNG, or WebP image.")
        return avatar
