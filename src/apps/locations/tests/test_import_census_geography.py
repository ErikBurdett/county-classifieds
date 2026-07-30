from __future__ import annotations

import hashlib
import zipfile
from datetime import date
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.locations.models import County, ReferenceImport, State

pytestmark = pytest.mark.django_db


def write_gazetteer_archive(tmp_path: Path, contents: str) -> tuple[Path, str]:
    source_path = tmp_path / "2025_Gaz_counties_national.zip"
    with zipfile.ZipFile(source_path, "w") as archive:
        archive.writestr("2025_Gaz_counties_national.txt", contents)
    return source_path, hashlib.sha256(source_path.read_bytes()).hexdigest()


def import_command(source_path: Path, checksum: str, *extra_arguments: str) -> None:
    call_command(
        "import_census_geography",
        str(source_path),
        "--expected-sha256",
        checksum,
        "--release-date",
        date(2025, 1, 1).isoformat(),
        *extra_arguments,
    )


def test_import_is_idempotent_and_preserves_network_controls(tmp_path: Path) -> None:
    source_path, checksum = write_gazetteer_archive(
        tmp_path,
        "GEOID\tNAME\n48375\tPotter County\n48381\tRandall County\n",
    )

    import_command(source_path, checksum)
    texas = State.objects.get(fips="48")
    potter = County.objects.get(fips="48375")
    assert texas.is_active and texas.is_network_enabled
    assert potter.is_active and potter.is_network_enabled
    texas.is_active = True
    texas.is_network_enabled = True
    texas.save()
    potter.is_active = True
    potter.is_network_enabled = True
    potter.save()

    import_command(source_path, checksum)

    texas.refresh_from_db()
    potter.refresh_from_db()
    assert State.objects.count() == 1
    assert County.objects.count() == 2
    assert ReferenceImport.objects.count() == 2
    assert texas.is_active and texas.is_network_enabled
    assert potter.is_active and potter.is_network_enabled
    latest_import = ReferenceImport.objects.first()
    assert latest_import is not None
    assert latest_import.states_unchanged_count == 1
    assert latest_import.counties_unchanged_count == 2
    assert latest_import.states_created_count == latest_import.counties_created_count == 0


def test_invalid_header_and_checksum_leave_no_rows(tmp_path: Path) -> None:
    source_path, checksum = write_gazetteer_archive(tmp_path, "GEOID\tLABEL\n48375\tPotter\n")

    with pytest.raises(CommandError, match="header"):
        import_command(source_path, checksum)
    with pytest.raises(CommandError, match="checksum"):
        import_command(source_path, "0" * 64)

    assert not State.objects.exists()
    assert not County.objects.exists()
    assert not ReferenceImport.objects.exists()


def test_import_accepts_official_pipe_delimited_gazetteer(tmp_path: Path) -> None:
    source_path, checksum = write_gazetteer_archive(
        tmp_path,
        "USPS|GEOID|NAME\nTX|48375|Potter County\n",
    )

    import_command(source_path, checksum)

    assert State.objects.get(fips="48").name == "Texas"
    assert County.objects.get(fips="48375").name == "Potter"


def test_import_backfills_census_internal_points_idempotently(tmp_path: Path) -> None:
    source_path, checksum = write_gazetteer_archive(
        tmp_path,
        "USPS|GEOID|NAME|INTPTLAT|INTPTLONG\nTX|48375|Potter County|35.401010|-101.894020\n",
    )

    import_command(source_path, checksum)
    potter = County.objects.get(fips="48375")
    assert str(potter.centroid_latitude) == "35.401010"
    assert str(potter.centroid_longitude) == "-101.894020"

    import_command(source_path, checksum)
    potter.refresh_from_db()
    assert str(potter.centroid_latitude) == "35.401010"
    assert County.objects.count() == 1


def test_import_without_internal_points_leaves_centroids_empty(tmp_path: Path) -> None:
    source_path, checksum = write_gazetteer_archive(
        tmp_path,
        "GEOID\tNAME\n48375\tPotter County\n",
    )

    import_command(source_path, checksum)

    potter = County.objects.get(fips="48375")
    assert potter.centroid_latitude is None
    assert potter.centroid_longitude is None


def test_import_preserves_city_suffix_when_a_county_has_the_same_name(tmp_path: Path) -> None:
    source_path, checksum = write_gazetteer_archive(
        tmp_path,
        "USPS|GEOID|NAME\nMD|24005|Baltimore County\nMD|24510|Baltimore city\n",
    )

    import_command(source_path, checksum)

    assert County.objects.get(fips="24005").slug == "baltimore"
    assert County.objects.get(fips="24510").slug == "baltimore-city"


def test_enable_nationwide_directory_updates_all_location_flags() -> None:
    texas = State.objects.create(
        fips="48",
        usps_code="TX",
        name="Texas",
        slug="texas",
    )
    potter = County.objects.create(
        fips="48375",
        state=texas,
        name="Potter",
        slug="potter",
    )

    call_command("enable_nationwide_directory")

    texas.refresh_from_db()
    potter.refresh_from_db()
    assert texas.is_active and texas.is_network_enabled
    assert potter.is_active and potter.is_network_enabled


def test_dry_run_and_unknown_state_fips_leave_no_rows(tmp_path: Path) -> None:
    source_path, checksum = write_gazetteer_archive(
        tmp_path,
        "GEOID\tNAME\n48375\tPotter County\n",
    )

    import_command(source_path, checksum, "--dry-run")

    assert not State.objects.exists()
    assert not County.objects.exists()
    assert not ReferenceImport.objects.exists()

    invalid_source_path, invalid_checksum = write_gazetteer_archive(
        tmp_path,
        "GEOID\tNAME\n99001\tUnknown County\n",
    )
    with pytest.raises(CommandError, match="unknown state FIPS"):
        import_command(invalid_source_path, invalid_checksum)
    assert not State.objects.exists()
