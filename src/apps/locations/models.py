from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models

SHA256_HEX_LENGTH = 64


class State(models.Model):
    fips = models.CharField(max_length=2, unique=True)
    usps_code = models.CharField(max_length=2, unique=True)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=False)
    is_network_enabled = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fips__regex=r"^\d{2}$"), name="locations_state_fips"
            ),
            models.CheckConstraint(
                condition=models.Q(usps_code__regex=r"^[A-Z]{2}$"),
                name="locations_state_usps_code",
            ),
        ]
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        self.fips = self.fips.zfill(2)
        self.usps_code = self.usps_code.upper()
        self.slug = self.slug.lower()
        if self.is_network_enabled and not self.is_active:
            raise ValidationError("A network-enabled state must be active.")


class County(models.Model):
    fips = models.CharField(max_length=5, unique=True)
    state = models.ForeignKey(State, on_delete=models.PROTECT, related_name="counties")
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    centroid_latitude = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Public Census county internal-point latitude; not seller location data.",
    )
    centroid_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Public Census county internal-point longitude; not seller location data.",
    )
    is_active = models.BooleanField(default=False)
    is_network_enabled = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("state", "slug"), name="locations_county_state_slug_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(fips__regex=r"^\d{5}$"), name="locations_county_fips"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(centroid_latitude__isnull=True)
                    | models.Q(centroid_latitude__gte=-90, centroid_latitude__lte=90)
                ),
                name="locations_county_centroid_latitude_range",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(centroid_longitude__isnull=True)
                    | models.Q(centroid_longitude__gte=-180, centroid_longitude__lte=180)
                ),
                name="locations_county_centroid_longitude_range",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        centroid_latitude__isnull=True,
                        centroid_longitude__isnull=True,
                    )
                    | models.Q(
                        centroid_latitude__isnull=False,
                        centroid_longitude__isnull=False,
                    )
                ),
                name="locations_county_centroid_pair",
            ),
        ]
        indexes = [
            models.Index(
                fields=("centroid_latitude", "centroid_longitude"),
                name="locations_county_centroid_idx",
            ),
        ]
        ordering = ("state__name", "name")

    def __str__(self) -> str:
        return f"{self.name}, {self.state.usps_code}"

    def clean(self) -> None:
        super().clean()
        self.fips = self.fips.zfill(5)
        self.slug = self.slug.lower()
        if self.fips[:2] != self.state.fips:
            raise ValidationError({"fips": "County FIPS must begin with its state's FIPS."})
        if (self.centroid_latitude is None) != (self.centroid_longitude is None):
            raise ValidationError(
                "County centroid latitude and longitude must be provided together."
            )
        if self.is_network_enabled and (not self.is_active or not self.state.is_active):
            raise ValidationError("A network-enabled county and its state must be active.")


class ReferenceImport(models.Model):
    """An append-only operational record for a validated reference-data import."""

    source_name = models.CharField(max_length=255)
    source_url = models.URLField(max_length=500)
    release_version = models.CharField(max_length=50)
    release_date = models.DateField()
    sha256_checksum = models.CharField(max_length=64)
    transformation_version = models.CharField(max_length=50)
    source_state_count = models.PositiveIntegerField()
    source_county_count = models.PositiveIntegerField()
    states_created_count = models.PositiveIntegerField()
    states_updated_count = models.PositiveIntegerField()
    states_unchanged_count = models.PositiveIntegerField()
    counties_created_count = models.PositiveIntegerField()
    counties_updated_count = models.PositiveIntegerField()
    counties_unchanged_count = models.PositiveIntegerField()
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-imported_at",)

    def __str__(self) -> str:
        return f"{self.source_name} {self.release_version} ({self.imported_at:%Y-%m-%d})"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise ValidationError("Reference import records are immutable.")
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        self.sha256_checksum = self.sha256_checksum.lower()
        if len(self.sha256_checksum) != SHA256_HEX_LENGTH or any(
            character not in "0123456789abcdef" for character in self.sha256_checksum
        ):
            raise ValidationError({"sha256_checksum": "Enter a lowercase SHA256 checksum."})


class ZipCountyReference(models.Model):
    """A ZIP-to-county candidate from a versioned, offline source crosswalk."""

    postal_code = models.CharField(max_length=5)
    county = models.ForeignKey(County, on_delete=models.PROTECT, related_name="zip_candidates")
    source_name = models.CharField(max_length=255)
    source_url = models.URLField(max_length=500)
    release_version = models.CharField(max_length=50)
    release_date = models.DateField()
    sha256_checksum = models.CharField(max_length=64)
    transformation_version = models.CharField(max_length=50)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("postal_code", "county"), name="locations_zip_county_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(postal_code__regex=r"^\d{5}$"),
                name="locations_zip_code_format",
            ),
        ]
        indexes = [
            models.Index(fields=("postal_code", "county"), name="locations_zip_lookup_idx"),
        ]
        ordering = ("postal_code", "county__name")

    def __str__(self) -> str:
        return f"{self.postal_code}: {self.county_id}"

    def clean(self) -> None:
        super().clean()
        self.postal_code = self.postal_code.strip()
        self.sha256_checksum = self.sha256_checksum.lower()
        if len(self.sha256_checksum) != SHA256_HEX_LENGTH or any(
            character not in "0123456789abcdef" for character in self.sha256_checksum
        ):
            raise ValidationError({"sha256_checksum": "Enter a lowercase SHA256 checksum."})
