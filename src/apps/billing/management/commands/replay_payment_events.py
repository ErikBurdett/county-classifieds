from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.billing.selectors import replayable_events
from apps.billing.services import process_payment_event


class Command(BaseCommand):
    help = "Replay received or failed durable payment events through the normal handler."

    def handle(self, *_args: object, **_options: object) -> None:
        processed = 0
        for event in replayable_events():
            process_payment_event(event_id=event.id)
            processed += 1
        self.stdout.write(self.style.SUCCESS(f"Replayed {processed} payment event(s)."))
