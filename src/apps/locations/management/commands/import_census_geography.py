from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.locations.services import (
    GeographyImportError,
    ImportCounts,
    ImportMetadata,
    import_census_geography,
)

DEFAULT_SOURCE_NAME = "U.S. Census Bureau National Counties Gazetteer"
DEFAULT_SOURCE_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "2025_Gazetteer/2025_Gaz_counties_national.zip"
)


class Command(BaseCommand):
    help = "Import a validated local U.S. Census National Counties Gazetteer archive."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("source_path", type=Path)
        parser.add_argument("--expected-sha256", required=True)
        parser.add_argument("--release-date", required=True, type=date.fromisoformat)
        parser.add_argument("--release-version", default="2025")
        parser.add_argument("--source-name", default=DEFAULT_SOURCE_NAME)
        parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *_args: Any, **options: Any) -> None:
        try:
            counts = import_census_geography(
                source_path=options["source_path"],
                expected_sha256=options["expected_sha256"],
                metadata=ImportMetadata(
                    source_name=options["source_name"],
                    source_url=options["source_url"],
                    release_version=options["release_version"],
                    release_date=options["release_date"],
                ),
                dry_run=options["dry_run"],
            )
        except (GeographyImportError, OSError, ValidationError) as error:
            raise CommandError(str(error)) from error

        self.stdout.write(self.style.SUCCESS(self._result_message(counts, options["dry_run"])))

    @staticmethod
    def _result_message(counts: ImportCounts, dry_run: bool) -> str:
        prefix = "Dry run validated" if dry_run else "Imported"
        return (
            f"{prefix}: {counts.source_state_count} states and {counts.source_county_count} "
            f"counties; states created/updated/unchanged "
            f"{counts.states_created_count}/{counts.states_updated_count}/"
            f"{counts.states_unchanged_count}; counties created/updated/unchanged "
            f"{counts.counties_created_count}/{counts.counties_updated_count}/"
            f"{counts.counties_unchanged_count}."
        )
