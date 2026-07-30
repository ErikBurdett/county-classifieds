from __future__ import annotations

import hashlib
from datetime import date
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.locations.models import County, State, ZipCountyReference
from apps.locations.zip_county import (
    ZipCountyImportError,
    ZipCountyImportMetadata,
    import_hud_zip_county_crosswalk,
    zip_county_candidates,
)

pytestmark = pytest.mark.django_db


def _metadata() -> ZipCountyImportMetadata:
    return ZipCountyImportMetadata(
        source_name="Test ZIP-to-county source",
        source_url="https://example.test/zip-county-source",
        release_version="test",
        release_date=date(2026, 7, 23),
    )


def test_imports_and_looks_up_offline_zip_county_candidates(tmp_path: Path) -> None:
    state = State.objects.create(
        fips="48", usps_code="TX", name="Texas", slug="texas", is_active=True
    )
    county = County.objects.create(
        fips="48375", state=state, name="Potter", slug="potter", is_active=True
    )
    source = tmp_path / "ZIP_COUNTY.csv"
    payload = b"ZIP,COUNTY\n79101,48375\n"
    source.write_bytes(payload)
    counts = import_hud_zip_county_crosswalk(
        source_path=source,
        expected_sha256=hashlib.sha256(payload).hexdigest(),
        metadata=_metadata(),
        dry_run=False,
    )
    assert counts.candidates_created == 1
    assert ZipCountyReference.objects.count() == 1
    assert zip_county_candidates(postal_code="79101", state_id=state.id) == [county]
    repeat = import_hud_zip_county_crosswalk(
        source_path=source,
        expected_sha256=hashlib.sha256(payload).hexdigest(),
        metadata=_metadata(),
        dry_run=True,
    )
    assert repeat.candidates_unchanged == 1
    assert zip_county_candidates(postal_code="bad", state_id=state.id) == []


def test_imports_harvard_dataverse_tab_crosswalk_with_multiple_counties(
    tmp_path: Path,
) -> None:
    state = State.objects.create(
        fips="48", usps_code="TX", name="Texas", slug="texas", is_active=True
    )
    first_county = County.objects.create(
        fips="48375", state=state, name="Potter", slug="potter", is_active=True
    )
    second_county = County.objects.create(
        fips="48381", state=state, name="Randall", slug="randall", is_active=True
    )
    source = tmp_path / "one2few_summy.tsv"
    payload = (
        b" zip \t county \ttop_match\tmin_year\tmax_year\ttotal_matches\t"
        b"tot_ratio_avg\ttot_ratio_min\ttot_ratio_max\n"
        b"79101\t48375\t1\t2010\t2023\t14\t0.9\t0.8\t1.0\n"
        b"79101\t48381\t0\t2010\t2023\t14\t0.1\t0.0\t0.2\n"
    )
    source.write_bytes(payload)

    counts = import_hud_zip_county_crosswalk(
        source_path=source,
        expected_sha256=hashlib.sha256(payload).hexdigest(),
        metadata=ZipCountyImportMetadata(
            source_name="Harvard Dataverse one2few_summy",
            source_url="https://doi.org/10.7910/DVN/0U2TCB",
            release_version="2024-08-12",
            release_date=date(2024, 8, 12),
        ),
        dry_run=False,
    )

    assert counts.rows_read == 2
    assert counts.candidates_created == 2
    assert zip_county_candidates(postal_code="79101", state_id=state.id) == [
        first_county,
        second_county,
    ]
    first_candidate = ZipCountyReference.objects.get(postal_code="79101", county=first_county)
    assert first_candidate.source_name == "Harvard Dataverse one2few_summy"
    assert first_candidate.source_url == "https://doi.org/10.7910/DVN/0U2TCB"


def test_skips_well_formed_counties_absent_from_imported_geography(
    tmp_path: Path,
) -> None:
    state = State.objects.create(
        fips="48", usps_code="TX", name="Texas", slug="texas", is_active=True
    )
    county = County.objects.create(
        fips="48375", state=state, name="Potter", slug="potter", is_active=True
    )
    source = tmp_path / "one2few_summy.tsv"
    payload = (
        b"zip\tcounty\ttop_match\tmin_year\tmax_year\ttotal_matches\t"
        b"tot_ratio_avg\ttot_ratio_min\ttot_ratio_max\n"
        b"79101\t48375\t1\t2010\t2023\t14\t0.9\t0.8\t1.0\n"
        b"00802\t78030\t1\t2010\t2023\t14\t0.9\t0.8\t1.0\n"
    )
    source.write_bytes(payload)

    counts = import_hud_zip_county_crosswalk(
        source_path=source,
        expected_sha256=hashlib.sha256(payload).hexdigest(),
        metadata=_metadata(),
        dry_run=False,
    )

    assert counts.rows_read == 2
    assert counts.rows_skipped_missing_county == 1
    assert counts.candidates_created == 1
    assert ZipCountyReference.objects.get().county == county

    dry_run_counts = import_hud_zip_county_crosswalk(
        source_path=source,
        expected_sha256=hashlib.sha256(payload).hexdigest(),
        metadata=_metadata(),
        dry_run=True,
    )
    assert dry_run_counts.rows_skipped_missing_county == 1
    assert dry_run_counts.candidates_unchanged == 1
    assert ZipCountyReference.objects.count() == 1

    output = StringIO()
    call_command(
        "import_hud_zip_counties",
        source,
        expected_sha256=hashlib.sha256(payload).hexdigest(),
        release_date="2026-07-23",
        release_version="test",
        source_name="Test ZIP-to-county source",
        source_url="https://example.test/zip-county-source",
        stdout=output,
    )
    assert "Skipped 1 rows with county FIPS absent from imported geography." in output.getvalue()
    assert "1 skipped for missing counties" in output.getvalue()


def test_rejects_source_without_counties_in_imported_geography(tmp_path: Path) -> None:
    source = tmp_path / "ZIP_COUNTY.csv"
    payload = b"ZIP,COUNTY\n00802,78030\n"
    source.write_bytes(payload)

    with pytest.raises(ZipCountyImportError, match="no county FIPS present"):
        import_hud_zip_county_crosswalk(
            source_path=source,
            expected_sha256=hashlib.sha256(payload).hexdigest(),
            metadata=_metadata(),
            dry_run=False,
        )

    assert ZipCountyReference.objects.count() == 0


def test_rejects_unrecognized_crosswalk_schema_without_writing_rows(tmp_path: Path) -> None:
    state = State.objects.create(
        fips="48", usps_code="TX", name="Texas", slug="texas", is_active=True
    )
    County.objects.create(fips="48375", state=state, name="Potter", slug="potter", is_active=True)
    source = tmp_path / "unsupported.csv"
    payload = b"ZIP,COUNTY,UNEXPECTED\n79101,48375,invalid\n"
    source.write_bytes(payload)

    with pytest.raises(ZipCountyImportError, match="Expected a HUD CSV"):
        import_hud_zip_county_crosswalk(
            source_path=source,
            expected_sha256=hashlib.sha256(payload).hexdigest(),
            metadata=_metadata(),
            dry_run=False,
        )

    assert ZipCountyReference.objects.count() == 0
