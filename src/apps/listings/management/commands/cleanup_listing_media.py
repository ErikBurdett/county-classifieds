from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.listings.models import UploadSession, UploadSessionState


class Command(BaseCommand):
    help = "Remove expired, unfinalized listing-image staging files safely and idempotently."

    def handle(self, *args: Any, **options: Any) -> None:
        del args, options
        now = timezone.now()
        expired = UploadSession.objects.filter(
            state=UploadSessionState.OPEN,
            expires_at__lte=now,
        )
        removed_sessions = 0
        for session in expired.iterator():
            if session.staged_key:
                default_storage.delete(session.staged_key)
            session.state = UploadSessionState.EXPIRED
            session.save(update_fields=("state",))
            removed_sessions += 1

        referenced = set(
            UploadSession.objects.exclude(staged_key="").values_list("staged_key", flat=True)
        )
        removed_files = self._delete_abandoned_staging_files(referenced=referenced, now=now)
        message = (
            f"Expired {removed_sessions} upload sessions; "
            f"removed {removed_files} abandoned staged files."
        )
        self.stdout.write(self.style.SUCCESS(message))

    def _delete_abandoned_staging_files(self, *, referenced: set[str], now: Any) -> int:
        try:
            _directories, files = default_storage.listdir("staging")
        except FileNotFoundError:
            return 0
        removed = 0
        oldest_safe_time = now - timedelta(minutes=30)
        for filename in files:
            key = f"staging/{filename}"
            if key in referenced:
                continue
            try:
                modified_time = default_storage.get_modified_time(key)
            except FileNotFoundError:
                continue
            if modified_time <= oldest_safe_time:
                default_storage.delete(key)
                removed += 1
        return removed
