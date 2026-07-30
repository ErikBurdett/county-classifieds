from __future__ import annotations

from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .managers import UserManager
from .models import User


class MarketplaceUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email",)

    def clean_email(self) -> str:
        email = str(self.cleaned_data["email"])
        return UserManager.normalize_marketplace_email(email)


class MarketplaceUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"

    def clean_email(self) -> str:
        email = str(self.cleaned_data["email"])
        return UserManager.normalize_marketplace_email(email)
