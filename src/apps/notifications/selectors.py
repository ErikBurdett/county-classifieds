from __future__ import annotations

from django.db.models import QuerySet

from apps.accounts.models import User

from .models import UserNotification

HEADER_NOTIFICATION_LIMIT = 5


def notifications_for_recipient(*, recipient: User) -> QuerySet[UserNotification]:
    return UserNotification.objects.filter(recipient=recipient)


def unread_notification_count(*, recipient: User) -> int:
    return notifications_for_recipient(recipient=recipient).filter(read_at__isnull=True).count()


def header_notifications_for_recipient(*, recipient: User) -> QuerySet[UserNotification]:
    return notifications_for_recipient(recipient=recipient)[:HEADER_NOTIFICATION_LIMIT]
