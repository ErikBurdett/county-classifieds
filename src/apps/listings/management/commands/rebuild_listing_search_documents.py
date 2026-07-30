from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from apps.listings.models import Listing
from apps.listings.search import postgres_search_available, rebuild_public_search_document


class Command(BaseCommand):
    help = (
        "Idempotently rebuild PostgreSQL public listing search documents in deterministic batches."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--batch-size", type=int, default=250)
        parser.add_argument("--max-batches", type=int, default=None)

    def handle(self, *_args: object, **options: object) -> None:
        if not postgres_search_available():
            raise CommandError("PostgreSQL is required to rebuild listing search documents.")
        batch_size = options["batch_size"]
        max_batches = options["max_batches"]
        if not isinstance(batch_size, int) or batch_size < 1:
            raise CommandError("--batch-size must be a positive integer.")
        if max_batches is not None and (not isinstance(max_batches, int) or max_batches < 1):
            raise CommandError("--max-batches must be a positive integer.")

        processed = 0
        batches = 0
        last_id: str | None = None
        queryset = Listing.objects.order_by("id")
        while max_batches is None or batches < max_batches:
            page = queryset if last_id is None else queryset.filter(id__gt=last_id)
            listing_ids = list(page.values_list("id", flat=True)[:batch_size])
            if not listing_ids:
                break
            with transaction.atomic():
                listings = (
                    Listing.objects.filter(id__in=listing_ids)
                    .select_related(
                        "category",
                        "category__posting_profile",
                        "vertical",
                        "auto_details",
                        "ag_equipment_details",
                        "home_details",
                        "home_goods_details",
                        "livestock_details",
                        "pasture_details",
                        "rental_details",
                        "generic_details",
                    )
                    .prefetch_related(
                        "category__posting_profile__fields",
                        "controlled_tags__category",
                        "seller_tags",
                    )
                    .order_by("id")
                )
                for listing in listings:
                    rebuild_public_search_document(listing=listing)
                    processed += 1
            last_id = str(listing_ids[-1])
            batches += 1
        self.stdout.write(self.style.SUCCESS(f"Rebuilt {processed} listing search documents."))
