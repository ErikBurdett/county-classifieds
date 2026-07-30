from __future__ import annotations

from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import Min
from django.utils import timezone

from apps.core.models import OutboxEvent
from apps.core.outbox import replay_failed_event


class Command(BaseCommand):
    help = "Inspect durable outbox backlog or explicitly replay one failed event."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--replay")

    def handle(self, *_args: object, **options: Any) -> None:
        event_id = options.get("replay")
        if event_id:
            event = replay_failed_event(event_id=event_id)
            self.stdout.write(self.style.SUCCESS(f"Replayed {event.id}."))
            return
        pending = OutboxEvent.objects.filter(processed_at__isnull=True, failed_at__isnull=True)
        oldest = pending.aggregate(oldest=Min("available_at"))["oldest"]
        age_seconds = None if oldest is None else int((timezone.now() - oldest).total_seconds())
        failed_count = OutboxEvent.objects.filter(failed_at__isnull=False).count()
        self.stdout.write(
            f"pending={pending.count()} failed={failed_count} "
            f"oldest_pending_age_seconds={age_seconds if age_seconds is not None else 'none'}"
        )
