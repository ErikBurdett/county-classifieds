from __future__ import annotations

from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from apps.accounts.models import User


class StaffAuthenticationForm(AuthenticationForm):
    """Authenticate only staff users without revealing why a login failed."""

    def confirm_login_allowed(self, user: User) -> None:
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise ValidationError(
                "Please enter a correct email and password.",
                code="invalid_login",
            )
