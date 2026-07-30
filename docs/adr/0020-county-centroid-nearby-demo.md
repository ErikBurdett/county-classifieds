# ADR-0020: County-centroid nearby-listings demo

**Status:** Accepted  
**Date:** 2026-07-23  
**Decision owners:** Project owner

## Decision

County browse pages may show a bounded rail of public listings from other
counties using the public U.S. Census National Counties Gazetteer `INTPTLAT`
and `INTPTLONG` internal-point fields. The selected range is 10–250 miles in
10-mile increments, defaults to 50 miles, and is measured between county
internal points.

This is a local-demo approximation. It is not radius search from a buyer,
seller, address, ZIP code, or listing, and it does not permit any private
address or geocode to enter a public query or template. State pages, maps,
seller flows, API, sitemap, and external map calls remain out of scope.

## Consequences

- Counties without both imported internal-point coordinates simply have no
  nearby rail. A Gazetteer fixture without those columns imports safely with
  empty coordinates; operators must import a coordinate-bearing 2025 artifact
  before expecting nearby results.
- Large, irregular, or geographically discontinuous counties can produce
  misleading apparent distance. Public copy calls the value approximate.
- The selector retains the shared `public_listings()` visibility boundary,
  excludes the current county, caps results, and orders nearest county first.
- A later genuine radius-search proposal requires a new precision/privacy
  decision and data model; this ADR does not alter the Phase 1A non-goal.

## Data and operations

The additive `County` coordinate columns are nullable and indexed as a pair.
The checksum-validated, offline Census importer idempotently updates existing
county rows from the supplied source artifact and records its existing
version/checksum provenance record. No external service is called.

## Security and privacy

Coordinates are public Census reference values only. Seller private street
addresses, postal codes, manually supplied localities, and any listing
geocodes are neither read nor exposed by the rail.

## Validation

Tests cover importer idempotence, null coordinates, range validation, public
visibility, county exclusion, distance bounds, server-rendered GET state, and
browser slider interaction.
