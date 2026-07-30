from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.listings.services import schedule_listing_reminders


class Command(BaseCommand):
    help = "Schedule unique 7/3/1-day listing-expiration reminder events."

    def handle(self, *_args: object, **_options: object) -> None:
        scheduled = schedule_listing_reminders()
        self.stdout.write(self.style.SUCCESS(f"Scheduled {scheduled} listing reminder(s)."))
