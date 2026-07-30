from __future__ import annotations

from django.contrib import admin

from .models import County, ReferenceImport, State


@admin.register(State)
class StateAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("name", "usps_code", "fips", "is_active", "is_network_enabled")
    list_filter = ("is_active", "is_network_enabled")
    search_fields = ("name", "usps_code", "fips")

    def has_delete_permission(self, _request, _obj=None) -> bool:  # type: ignore[no-untyped-def]
        return False


@admin.register(County)
class CountyAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = (
        "name",
        "state",
        "fips",
        "centroid_latitude",
        "centroid_longitude",
        "is_active",
        "is_network_enabled",
    )
    list_filter = ("state", "is_active", "is_network_enabled")
    search_fields = ("name", "fips")

    def has_delete_permission(self, _request, _obj=None) -> bool:  # type: ignore[no-untyped-def]
        return False


@admin.register(ReferenceImport)
class ReferenceImportAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = (
        "source_name",
        "release_version",
        "release_date",
        "source_county_count",
        "sha256_checksum",
        "imported_at",
    )
    search_fields = ("source_name", "release_version", "sha256_checksum")
    readonly_fields = (
        "source_name",
        "source_url",
        "release_version",
        "release_date",
        "sha256_checksum",
        "transformation_version",
        "source_state_count",
        "source_county_count",
        "states_created_count",
        "states_updated_count",
        "states_unchanged_count",
        "counties_created_count",
        "counties_updated_count",
        "counties_unchanged_count",
        "imported_at",
    )

    def has_add_permission(self, _request) -> bool:  # type: ignore[no-untyped-def]
        return False

    def has_change_permission(self, request, _obj=None) -> bool:  # type: ignore[no-untyped-def]
        return str(request.method) == "GET"

    def has_delete_permission(self, _request, _obj=None) -> bool:  # type: ignore[no-untyped-def]
        return False
