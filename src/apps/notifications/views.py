from __future__ import annotations

from typing import cast
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import User

from .selectors import notifications_for_recipient
from .services import mark_all_notifications_read, mark_notification_read


@login_required
def feed(request: HttpRequest) -> HttpResponse:
    recipient = cast(User, request.user)
    return render(
        request,
        "notifications/feed.html",
        {"notifications": notifications_for_recipient(recipient=recipient)},
    )


@login_required
@require_POST
def mark_read(request: HttpRequest, notification_id: UUID) -> HttpResponse:
    recipient = cast(User, request.user)
    notification = mark_notification_read(recipient=recipient, notification_id=notification_id)
    if notification is None:
        messages.error(request, "Notification not found.")
    return redirect("notifications:feed")


@login_required
def visit(request: HttpRequest, notification_id: UUID) -> HttpResponse:
    """Mark an owned notification read before following its safe destination."""
    recipient = cast(User, request.user)
    notification = (
        notifications_for_recipient(recipient=recipient).filter(pk=notification_id).first()
    )
    if notification is None:
        raise Http404
    mark_notification_read(recipient=recipient, notification_id=notification.id)
    return redirect(notification.destination_url or "notifications:feed")


@login_required
@require_POST
def mark_all_read(request: HttpRequest) -> HttpResponse:
    mark_all_notifications_read(recipient=cast(User, request.user))
    return redirect("notifications:feed")
