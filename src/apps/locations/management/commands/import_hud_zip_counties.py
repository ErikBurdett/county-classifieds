from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.locations.zip_county import (
    ZipCountyImportError,
    ZipCountyImportMetadata,
    import_hud_zip_county_crosswalk,
)


class Command(BaseCommand):
    help = (
        "Import a validated local ZIP-to-county crosswalk: HUD CSV or Harvard "
        "Dataverse one2few_summy TSV."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("source_path", type=Path)
        parser.add_argument("--expected-sha256", required=True)
        parser.add_argument("--release-date", required=True, type=date.fromisoformat)
        parser.add_argument("--release-version", required=True)
        parser.add_argument(
            "--source-name",
            required=True,
            help="Record the source name exactly as supplied by the operator.",
        )
        parser.add_argument(
            "--source-url",
            required=True,
            help="Record the source URL exactly as supplied by the operator.",
        )
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *_args: Any, **options: Any) -> None:
        try:
            counts = import_hud_zip_county_crosswalk(
                source_path=options["source_path"],
                expected_sha256=options["expected_sha256"],
                metadata=ZipCountyImportMetadata(
                    source_name=options["source_name"],
                    source_url=options["source_url"],
                    release_version=options["release_version"],
                    release_date=options["release_date"],
                ),
                dry_run=options["dry_run"],
            )
        except (OSError, ZipCountyImportError) as error:
            raise CommandError(str(error)) from error
        prefix = "Dry run validated" if options["dry_run"] else "Imported"
        if counts.rows_skipped_missing_county:
            self.stdout.write(
                self.style.WARNING(
                    "Skipped "
                    f"{counts.rows_skipped_missing_county} rows with county FIPS "
                    "absent from imported geography."
                )
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}: {counts.rows_read} rows; "
                f"{counts.rows_skipped_missing_county} skipped for missing counties; "
                f"{counts.candidates_created} candidates created and "
                f"{counts.candidates_unchanged} unchanged."
            )
        )
