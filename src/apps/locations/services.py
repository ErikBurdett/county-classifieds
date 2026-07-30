from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

from django.db import transaction
from django.utils.text import slugify

from .models import County, ReferenceImport, State

TRANSFORMATION_VERSION = "2025-national-counties-v2"
REQUIRED_GAZETTEER_HEADERS = frozenset({"GEOID", "NAME"})
CENTROID_GAZETTEER_HEADERS = frozenset({"INTPTLAT", "INTPTLONG"})
SHA256_HEX_LENGTH = 64
GEOID_LENGTH = 5
MIN_LATITUDE = Decimal("-90")
MAX_LATITUDE = Decimal("90")
MIN_LONGITUDE = Decimal("-180")
MAX_LONGITUDE = Decimal("180")

# State FIPS codes are stable Census reference identifiers. The national counties
# Gazetteer supplies county GEOIDs, not the corresponding state name/USPS columns.
CENSUS_STATES: dict[str, tuple[str, str]] = {
    "01": ("Alabama", "AL"),
    "02": ("Alaska", "AK"),
    "04": ("Arizona", "AZ"),
    "05": ("Arkansas", "AR"),
    "06": ("California", "CA"),
    "08": ("Colorado", "CO"),
    "09": ("Connecticut", "CT"),
    "10": ("Delaware", "DE"),
    "11": ("District of Columbia", "DC"),
    "12": ("Florida", "FL"),
    "13": ("Georgia", "GA"),
    "15": ("Hawaii", "HI"),
    "16": ("Idaho", "ID"),
    "17": ("Illinois", "IL"),
    "18": ("Indiana", "IN"),
    "19": ("Iowa", "IA"),
    "20": ("Kansas", "KS"),
    "21": ("Kentucky", "KY"),
    "22": ("Louisiana", "LA"),
    "23": ("Maine", "ME"),
    "24": ("Maryland", "MD"),
    "25": ("Massachusetts", "MA"),
    "26": ("Michigan", "MI"),
    "27": ("Minnesota", "MN"),
    "28": ("Mississippi", "MS"),
    "29": ("Missouri", "MO"),
    "30": ("Montana", "MT"),
    "31": ("Nebraska", "NE"),
    "32": ("Nevada", "NV"),
    "33": ("New Hampshire", "NH"),
    "34": ("New Jersey", "NJ"),
    "35": ("New Mexico", "NM"),
    "36": ("New York", "NY"),
    "37": ("North Carolina", "NC"),
    "38": ("North Dakota", "ND"),
    "39": ("Ohio", "OH"),
    "40": ("Oklahoma", "OK"),
    "41": ("Oregon", "OR"),
    "42": ("Pennsylvania", "PA"),
    "44": ("Rhode Island", "RI"),
    "45": ("South Carolina", "SC"),
    "46": ("South Dakota", "SD"),
    "47": ("Tennessee", "TN"),
    "48": ("Texas", "TX"),
    "49": ("Utah", "UT"),
    "50": ("Vermont", "VT"),
    "51": ("Virginia", "VA"),
    "53": ("Washington", "WA"),
    "54": ("West Virginia", "WV"),
    "55": ("Wisconsin", "WI"),
    "56": ("Wyoming", "WY"),
    "60": ("American Samoa", "AS"),
    "66": ("Guam", "GU"),
    "69": ("Northern Mariana Islands", "MP"),
    "72": ("Puerto Rico", "PR"),
    "78": ("U.S. Virgin Islands", "VI"),
}

COUNTY_SUFFIXES = (
    " City and Borough",
    " city and borough",
    " Census Area",
    " Municipality",
    " Borough",
    " County",
    " Parish",
)


class GeographyImportError(ValueError):
    """A local Census artifact failed validation before any database writes."""


@dataclass(frozen=True)
class GazetteerCounty:
    fips: str
    state_fips: str
    name: str
    slug: str
    centroid_latitude: Decimal | None
    centroid_longitude: Decimal | None


@dataclass(frozen=True)
class ImportCounts:
    source_state_count: int
    source_county_count: int
    states_created_count: int
    states_updated_count: int
    states_unchanged_count: int
    counties_created_count: int
    counties_updated_count: int
    counties_unchanged_count: int


@dataclass(frozen=True)
class ImportMetadata:
    source_name: str
    source_url: str
    release_version: str
    release_date: date


def import_census_geography(
    *,
    source_path: Path,
    expected_sha256: str,
    metadata: ImportMetadata,
    dry_run: bool = False,
) -> ImportCounts:
    """Validate a local Census archive, then idempotently apply its reference data."""
    normalized_checksum = _validate_expected_checksum(expected_sha256)
    actual_checksum = _calculate_checksum(source_path)
    if actual_checksum != normalized_checksum:
        raise GeographyImportError("The source checksum does not match the expected SHA256.")

    counties = _read_counties(source_path)
    state_fips_codes = {county.state_fips for county in counties}
    states = {
        fips: (name, usps_code, slugify(name))
        for fips, (name, usps_code) in CENSUS_STATES.items()
        if fips in state_fips_codes
    }

    with transaction.atomic():
        counts = _upsert_reference_data(states=states, counties=counties)
        if dry_run:
            transaction.set_rollback(True)
            return counts
        reference_import = ReferenceImport(
            source_name=metadata.source_name,
            source_url=metadata.source_url,
            release_version=metadata.release_version,
            release_date=metadata.release_date,
            sha256_checksum=actual_checksum,
            transformation_version=TRANSFORMATION_VERSION,
            **counts.__dict__,
        )
        reference_import.full_clean()
        reference_import.save()
    return counts


def _validate_expected_checksum(expected_sha256: str) -> str:
    checksum = expected_sha256.lower()
    if len(checksum) != SHA256_HEX_LENGTH or any(
        character not in "0123456789abcdef" for character in checksum
    ):
        raise GeographyImportError("Expected SHA256 must be a 64-character hexadecimal digest.")
    return checksum


def _calculate_checksum(source_path: Path) -> str:
    if not source_path.is_file():
        raise GeographyImportError("The source path must be a readable local file.")
    digest = hashlib.sha256()
    with source_path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_counties(source_path: Path) -> list[GazetteerCounty]:
    if not zipfile.is_zipfile(source_path):
        raise GeographyImportError("The Census source must be a ZIP archive.")
    with zipfile.ZipFile(source_path) as archive:
        invalid_member = archive.testzip()
        if invalid_member is not None:
            raise GeographyImportError(f"The archive is corrupt at {invalid_member!r}.")
        members = [
            member
            for member in archive.infolist()
            if not member.is_dir() and member.filename.lower().endswith(".txt")
        ]
        if len(members) != 1:
            raise GeographyImportError("The archive must contain exactly one Gazetteer text file.")
        with (
            archive.open(members[0]) as binary_file,
            io.TextIOWrapper(
                binary_file,
                encoding="utf-8-sig",
                newline="",
            ) as text_file,
        ):
            header = text_file.readline()
            delimiter = "|" if header.count("|") > header.count("\t") else "\t"
            text_file.seek(0)
            reader = csv.DictReader(text_file, delimiter=delimiter)
            if reader.fieldnames is None or not set(reader.fieldnames).issuperset(
                REQUIRED_GAZETTEER_HEADERS
            ):
                raise GeographyImportError("The Gazetteer header must include GEOID and NAME.")
            has_centroids = set(reader.fieldnames).issuperset(CENTROID_GAZETTEER_HEADERS)
            counties = [
                _parse_county_row(
                    cast(dict[str, str | None], row), row_number, has_centroids=has_centroids
                )
                for row_number, row in enumerate(reader, 2)
            ]

    if not counties:
        raise GeographyImportError("The Gazetteer source contains no county records.")
    _validate_counties(counties)
    return counties


def _parse_county_row(
    row: dict[str, str | None], row_number: int, *, has_centroids: bool
) -> GazetteerCounty:
    geoid = (row.get("GEOID") or "").strip()
    source_name = (row.get("NAME") or "").strip()
    if len(geoid) != GEOID_LENGTH or not geoid.isdigit():
        raise GeographyImportError(f"Row {row_number} has an invalid GEOID.")
    if not source_name:
        raise GeographyImportError(f"Row {row_number} has an empty county name.")
    name = _display_county_name(source_name)
    county_slug = slugify(name)
    if not county_slug:
        raise GeographyImportError(f"Row {row_number} produces an empty county slug.")
    centroid_latitude, centroid_longitude = _parse_centroid(
        row=row, row_number=row_number, has_centroids=has_centroids
    )
    return GazetteerCounty(
        fips=geoid,
        state_fips=geoid[:2],
        name=name,
        slug=county_slug,
        centroid_latitude=centroid_latitude,
        centroid_longitude=centroid_longitude,
    )


def _parse_centroid(
    *, row: dict[str, str | None], row_number: int, has_centroids: bool
) -> tuple[Decimal | None, Decimal | None]:
    if not has_centroids:
        return None, None
    latitude_value = (row.get("INTPTLAT") or "").strip()
    longitude_value = (row.get("INTPTLONG") or "").strip()
    if not latitude_value and not longitude_value:
        return None, None
    try:
        latitude = Decimal(latitude_value)
        longitude = Decimal(longitude_value)
    except InvalidOperation as error:
        raise GeographyImportError(
            f"Row {row_number} has invalid internal-point coordinates."
        ) from error
    if not (
        MIN_LATITUDE <= latitude <= MAX_LATITUDE and MIN_LONGITUDE <= longitude <= MAX_LONGITUDE
    ):
        raise GeographyImportError(f"Row {row_number} has out-of-range internal-point coordinates.")
    return latitude.quantize(Decimal("0.000001")), longitude.quantize(Decimal("0.000001"))


def _display_county_name(source_name: str) -> str:
    for suffix in COUNTY_SUFFIXES:
        if source_name.endswith(suffix):
            return source_name[: -len(suffix)]
    return source_name


def _validate_counties(counties: list[GazetteerCounty]) -> None:
    seen_fips: set[str] = set()
    seen_state_slugs: set[tuple[str, str]] = set()
    for county in counties:
        if county.state_fips not in CENSUS_STATES:
            raise GeographyImportError(f"County GEOID {county.fips} has an unknown state FIPS.")
        if county.fips in seen_fips:
            raise GeographyImportError(f"Duplicate county GEOID {county.fips}.")
        state_slug = (county.state_fips, county.slug)
        if state_slug in seen_state_slugs:
            raise GeographyImportError(
                f"County GEOID {county.fips} duplicates route slug {county.slug!r} in its state."
            )
        seen_fips.add(county.fips)
        seen_state_slugs.add(state_slug)


def _upsert_reference_data(
    *,
    states: dict[str, tuple[str, str, str]],
    counties: list[GazetteerCounty],
) -> ImportCounts:
    existing_states = State.objects.in_bulk(states, field_name="fips")
    state_instances: dict[str, State] = {}
    states_created = states_updated = states_unchanged = 0

    for fips, (name, usps_code, state_slug) in states.items():
        state = existing_states.get(fips)
        if state is None:
            state = State.objects.create(
                fips=fips,
                name=name,
                usps_code=usps_code,
                slug=state_slug,
                is_active=True,
                is_network_enabled=True,
            )
            states_created += 1
        elif (state.name, state.usps_code, state.slug) != (name, usps_code, state_slug):
            state.name = name
            state.usps_code = usps_code
            state.slug = state_slug
            state.save(update_fields=("name", "usps_code", "slug"))
            states_updated += 1
        else:
            states_unchanged += 1
        state_instances[fips] = state

    existing_counties = County.objects.in_bulk(
        (county.fips for county in counties),
        field_name="fips",
    )
    counties_created = counties_updated = counties_unchanged = 0
    for county in counties:
        existing_county = existing_counties.get(county.fips)
        if existing_county is None:
            County.objects.create(
                fips=county.fips,
                state=state_instances[county.state_fips],
                name=county.name,
                slug=county.slug,
                centroid_latitude=county.centroid_latitude,
                centroid_longitude=county.centroid_longitude,
                is_active=True,
                is_network_enabled=True,
            )
            counties_created += 1
        elif (
            existing_county.state_id != state_instances[county.state_fips].id
            or existing_county.name != county.name
            or existing_county.slug != county.slug
            or existing_county.centroid_latitude != county.centroid_latitude
            or existing_county.centroid_longitude != county.centroid_longitude
        ):
            existing_county.state = state_instances[county.state_fips]
            existing_county.name = county.name
            existing_county.slug = county.slug
            existing_county.centroid_latitude = county.centroid_latitude
            existing_county.centroid_longitude = county.centroid_longitude
            existing_county.save(
                update_fields=(
                    "state",
                    "name",
                    "slug",
                    "centroid_latitude",
                    "centroid_longitude",
                )
            )
            counties_updated += 1
        else:
            counties_unchanged += 1

    return ImportCounts(
        source_state_count=len(states),
        source_county_count=len(counties),
        states_created_count=states_created,
        states_updated_count=states_updated,
        states_unchanged_count=states_unchanged,
        counties_created_count=counties_created,
        counties_updated_count=counties_updated,
        counties_unchanged_count=counties_unchanged,
    )
