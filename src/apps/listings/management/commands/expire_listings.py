from __future__ import annotations

from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand

from apps.listings.services import expire_due_listings


class Command(BaseCommand):
    help = "Expire due published listings in a locked, idempotent batch."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--batch-size", type=int, default=100)

    def handle(self, *_args: object, **options: Any) -> None:
        batch_size = int(options["batch_size"])
        if batch_size < 1:
            self.stderr.write("batch-size must be positive.")
            return
        expired = expire_due_listings(batch_size=batch_size)
        self.stdout.write(self.style.SUCCESS(f"Expired {expired} listing(s)."))
