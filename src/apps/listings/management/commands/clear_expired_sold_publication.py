from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.listings.models import Listing, ListingStatus


class Command(BaseCommand):
    help = "Clear expired public-retention timestamps from sold listings."

    def handle(self, *args: Any, **options: Any) -> None:
        del args, options
        cleared = Listing.objects.filter(
            status=ListingStatus.SOLD,
            sold_public_until__lte=timezone.now(),
        ).update(sold_public_until=None)
        self.stdout.write(self.style.SUCCESS(f"Cleared {cleared} expired sold listing(s)."))
