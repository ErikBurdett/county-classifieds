from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import County, ZipCountyReference

TRANSFORMATION_VERSION = "zip-county-crosswalk-v2"
FIPS_AND_ZIP_LENGTH = 5
HUD_CSV_HEADERS = (
    ("zip", "county"),
    ("zip", "county", "res_ratio", "bus_ratio", "oth_ratio", "tot_ratio"),
)
HARVARD_DATAVERSE_HEADERS = (
    "zip",
    "county",
    "top_match",
    "min_year",
    "max_year",
    "total_matches",
    "tot_ratio_avg",
    "tot_ratio_min",
    "tot_ratio_max",
)


class ZipCountyImportError(ValidationError):
    """The supplied offline ZIP/county reference file is invalid."""


@dataclass(frozen=True)
class ZipCountyImportMetadata:
    release_version: str
    release_date: date
    source_name: str
    source_url: str


@dataclass(frozen=True)
class ZipCountyImportCounts:
    rows_read: int
    rows_skipped_missing_county: int
    candidates_created: int
    candidates_unchanged: int


def zip_county_candidates(*, postal_code: str, state_id: int) -> list[County]:
    """Return only active, same-state offline reference candidates."""

    normalized = postal_code.strip()
    if len(normalized) != FIPS_AND_ZIP_LENGTH or not normalized.isdigit():
        return []
    return list(
        County.objects.filter(
            state_id=state_id,
            is_active=True,
            zip_candidates__postal_code=normalized,
        )
        .distinct()
        .order_by("name")
    )


def _source_sha256(source_path: Path) -> str:
    digest = hashlib.sha256()
    with source_path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_headers(row: list[str]) -> tuple[str, ...]:
    return tuple(value.strip().casefold() for value in row)


def _detect_crosswalk_format(header: list[str]) -> tuple[str, int, int]:
    normalized = _normalized_headers(header)
    if len(normalized) != len(set(normalized)):
        raise ZipCountyImportError("The source contains duplicate column names.")
    if normalized in HUD_CSV_HEADERS:
        return ",", 0, 1
    if normalized == HARVARD_DATAVERSE_HEADERS:
        return "\t", 0, 1
    raise ZipCountyImportError(
        "Expected a HUD CSV ZIP/COUNTY schema or the Harvard Dataverse "
        "one2few_summy tab-delimited schema."
    )


def _read_crosswalk_rows(source_path: Path) -> list[tuple[str, str]]:
    with source_path.open(newline="", encoding="utf-8-sig") as source:
        raw_header = source.readline()
        if not raw_header:
            raise ZipCountyImportError("The source is empty.")

    csv_header = next(csv.reader([raw_header], delimiter=","))
    tab_header = next(csv.reader([raw_header], delimiter="\t"))
    try:
        delimiter, postal_code_index, county_fips_index = _detect_crosswalk_format(csv_header)
    except ZipCountyImportError:
        delimiter, postal_code_index, county_fips_index = _detect_crosswalk_format(tab_header)
    header = csv_header if delimiter == "," else tab_header
    rows: list[tuple[str, str]] = []
    with source_path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.reader(source, delimiter=delimiter)
        next(reader)
        expected_column_count = len(header)
        try:
            for row_number, row in enumerate(reader, start=2):
                if len(row) != expected_column_count:
                    raise ZipCountyImportError(
                        f"The source has an invalid column count on row {row_number}."
                    )
                postal_code = row[postal_code_index].strip()
                county_fips = row[county_fips_index].strip()
                if len(postal_code) != FIPS_AND_ZIP_LENGTH or not postal_code.isdigit():
                    raise ZipCountyImportError(
                        f"The source contains an invalid ZIP code on row {row_number}."
                    )
                if len(county_fips) != FIPS_AND_ZIP_LENGTH or not county_fips.isdigit():
                    raise ZipCountyImportError(
                        f"The source contains an invalid county FIPS on row {row_number}."
                    )
                rows.append((postal_code, county_fips))
        except csv.Error as error:
            raise ZipCountyImportError("The source is not valid delimited text.") from error
    return rows


@transaction.atomic
def import_hud_zip_county_crosswalk(
    *,
    source_path: Path,
    expected_sha256: str,
    metadata: ZipCountyImportMetadata,
    dry_run: bool,
) -> ZipCountyImportCounts:
    actual_sha256 = _source_sha256(source_path)
    if actual_sha256 != expected_sha256.lower():
        raise ZipCountyImportError("The source SHA256 checksum did not match.")

    rows = _read_crosswalk_rows(source_path)
    counties_by_fips = County.objects.in_bulk(
        {county_fips for _, county_fips in rows},
        field_name="fips",
    )
    compatible_rows = [
        (postal_code, county_fips)
        for postal_code, county_fips in rows
        if county_fips in counties_by_fips
    ]
    skipped_missing_county = len(rows) - len(compatible_rows)
    if not compatible_rows:
        raise ZipCountyImportError("The source has no county FIPS present in imported geography.")

    created = unchanged = 0
    for postal_code, county_fips in compatible_rows:
        county = counties_by_fips[county_fips]
        defaults = {
            "source_name": metadata.source_name,
            "source_url": metadata.source_url,
            "release_version": metadata.release_version,
            "release_date": metadata.release_date,
            "sha256_checksum": actual_sha256,
            "transformation_version": TRANSFORMATION_VERSION,
        }
        candidate, was_created = ZipCountyReference.objects.get_or_create(
            postal_code=postal_code,
            county=county,
            defaults=defaults,
        )
        if was_created:
            created += 1
        else:
            unchanged += 1
            if not dry_run and any(
                getattr(candidate, field) != value for field, value in defaults.items()
            ):
                for field, value in defaults.items():
                    setattr(candidate, field, value)
                candidate.full_clean()
                candidate.save(update_fields=tuple(defaults))
    if dry_run:
        transaction.set_rollback(True)
    return ZipCountyImportCounts(
        rows_read=len(rows),
        rows_skipped_missing_county=skipped_missing_county,
        candidates_created=created,
        candidates_unchanged=unchanged,
    )
