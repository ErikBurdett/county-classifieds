from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from .selectors import header_notifications_for_recipient, unread_notification_count


def notification_center(request: HttpRequest) -> dict[str, Any]:
    """Supply recipient-scoped header state without querying for anonymous visitors."""
    if not request.user.is_authenticated or request.path.startswith("/manage/"):
        return {"header_notifications": (), "unread_notification_count": 0}
    return {
        "header_notifications": header_notifications_for_recipient(recipient=request.user),
        "unread_notification_count": unread_notification_count(recipient=request.user),
    }
