# M7 feature: Nearby county listings rail

**Status:** Accepted / implementing  
**Milestone:** M7  
**Decision:** DEC-114 / ADR-0020  
**Last updated:** 2026-07-23

## Outcome and scope

On a county browse page only, visitors can choose a 10–250 mile range in
10-mile increments and see up to 12 public listings from other counties whose
public Census county internal point is within that approximate range. The
origin is the current county internal point, default range is 50 miles, and
the normal GET parameter is `nearby_radius`.

The primary county feed remains separate. The rail spans all public verticals,
uses the shared public visibility selector, shows county/location and rounded
“about N miles away” copy, and never duplicates a current-county listing.

## Non-goals

This is not address, user, seller, ZIP, listing-coordinate, generic-location,
state-page, map, sitemap, API, or seller-dashboard radius search. It has no
PostGIS, geocoder, external service, or new dependency.

## Data and import

`County.centroid_latitude` and `County.centroid_longitude` are nullable public
Census reference values with paired-presence and geographic-range checks plus
a composite index. The offline checksum-validated 2025 Gazetteer importer
parses `INTPTLAT` and `INTPTLONG` when present and idempotently backfills
existing local counties while preserving marketplace activation controls.

A fixture lacking those columns leaves coordinates null intentionally; pages
omit the rail. Import a checked 2025 Gazetteer artifact with both columns to
enable nearby results. Existing source version, release date, URL, checksum,
and transformation version provenance remains recorded in `ReferenceImport`.

## Privacy, security, and limitations

Only public Census reference coordinates participate in the calculation.
Private seller addresses, postal codes, and any listing geocodes are not
queried, logged, placed in URLs, or rendered. Invalid ranges are form errors;
the selector independently rejects ranges outside 10–250 or not divisible by
10. The query has a bounded result cap and retains every `public_listings()`
visibility rule.

County internal points can be far from buyers and listings, especially in
large, irregular, or discontinuous counties. Copy labels this as approximate
county distance and must not claim true radius precision.

## SEO, accessibility, rollout, and rollback

The native labeled range input has a live `<output>` and ordinary GET fallback;
its query state is shareable. Existing query-page `noindex,follow` and
route-only canonical rules continue to apply. The rail is absent when origin
coordinates are unavailable.

Deploy the additive migration before importing coordinate-bearing Census data.
Rollback is to disable/remove the rail code; nullable coordinates remain safe
reference data. No seller data migration or external integration exists.

## Tests

Unit/request tests cover distance, current-county exclusion, public visibility,
null coordinates, range validation, rendering, query state, and privacy.
Importer tests cover parsed coordinates, missing columns, and reruns. Browser
coverage exercises the native slider/filter path. Migration SQL and local
PostgreSQL application are verified separately during implementation.
