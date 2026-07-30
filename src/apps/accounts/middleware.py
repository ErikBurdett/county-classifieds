from __future__ import annotations

from collections.abc import Callable

from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse

from .models import AccountStatus, User


class AccountStatusMiddleware:
    """Invalidate existing sessions after a status transition."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = request.user
        if (
            user.is_authenticated
            and isinstance(user, User)
            and (not user.is_active or user.account_status != AccountStatus.ACTIVE)
        ):
            logout(request)
        return self.get_response(request)
