# ADR 0010: Nationwide Geography Reference Data

**Status:** Accepted  
**Date:** 2026-07-23  
**Decision owners:** Project owner  
**Supersedes:** none  
**Superseded by:** none

## Context

The marketplace must support state and county browse scopes across the United
States while remaining one application and database. The source requirements
require normalized geography, FIPS provenance, and a gradual marketplace
rollout without treating counties as tenants.

## Decision drivers

- Stable, authoritative state and county identifiers
- Nationwide availability in one import
- A reversible, staff-controlled market activation policy
- Repeatable imports with source provenance

## Options considered

### Option A — Versioned U.S. Census Gazetteer dataset with separate activation

**Description:** Import all state and county records from the U.S. Census 2025
National Counties Gazetteer dataset. Store a separate marketplace-owned
network-active flag on location records.  
**Advantages:** Authoritative FIPS/GEOID data, nationwide coverage, traceable
source versions, and independent rollout control.  
**Disadvantages/risks:** Annual source updates require review and an importer
must preserve records referenced by marketplace data.  
**Cost/operability:** Small versioned source artifact and idempotent management
command; staff activation is administered through Django Admin.  
**Reversibility:** Activation flags can be changed without re-importing
reference data; a future source can supersede this ADR.

### Option B — Reuse the County Post application dataset

**Description:** Treat the news application’s current state/county dataset as
the marketplace source.  
**Advantages:** Existing local data and route familiarity.  
**Disadvantages/risks:** Its source version, provenance, and update lifecycle
are not an authoritative marketplace reference-data contract.  
**Cost/operability:** Would require reverse-engineering and maintaining an
unowned data pipeline.  
**Reversibility:** A later migration to an authoritative dataset risks route
and identifier drift.

## Decision

Effective 2026-07-23, use the U.S. Census Bureau 2025 National Counties
Gazetteer dataset as the initial nationwide state/county reference source.
Import all records in the dataset. The marketplace owns separate `is_active`
and `is_network_enabled` controls; staff use them to govern visible routes and
launch promotion without changing geography records.

## Rationale

The Census dataset provides the requested FIPS-based nationwide geography with
an explicit release year, while separate activation flags keep inventory and
marketing rollout operationally flexible.

## Consequences

### Positive

- State and county identifiers have a documented, reproducible source.
- All counties can exist in one shared database from the first import.
- Adding or activating a market is configuration, not deployment work.

### Negative/tradeoffs

- The importer must record release, checksum, source URL, and import counts.
- Deactivation must not delete records referenced by listings.

### Follow-up work

- [ ] Implement LOC-001 through LOC-003 from an accepted feature specification.
- [ ] Record the downloaded source checksum in the import manifest.
- [ ] Review future Census releases before replacing reference data.

## Security, privacy, and compliance impact

This public reference data contains no marketplace personal information.
Location activation must not expose private seller location data.

## Data/migration impact

Add normalized `State` and `County` reference tables and an idempotent import
command. Existing listings do not yet exist, so the first schema migration is
additive.

## Operational and cost impact

The source artifact is small. Admin staff own activation flags; imports run as
explicit commands and report changes.

## Validation

The import must validate FIPS/GEOID relationships, be idempotent, and record
its provenance. Canonical route tests must distinguish unknown, inactive, and
network-disabled locations.

## References

- `docs/14-OPEN-DECISIONS.md` DEC-002
- `docs/18-DATA-SEEDING.md`
- https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer/2025_Gaz_counties_national.zip
- https://www.census.gov/programs-surveys/geography/technical-documentation/records-layout/gaz-record-layouts/gaz25-record-layouts.html
