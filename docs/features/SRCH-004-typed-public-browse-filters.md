# SRCH-004 — Typed public browse filters

**Status:** Implemented locally  
**Milestone:** M7 public browse; M10 responsive enhancement  
**Authorization:** User-approved 2026-07-30

## Problem and scope

Buyers need compact structured filters for the existing public typed listing
presentations without an arbitrary query API, EAV filtering, or a client-side
search application. `PublicBrowseForm` renders typed controls only after the
buyer selects the corresponding vertical:

- Homes: property type, minimum beds/baths/square feet.
- Rentals: rental type, minimum beds, pets policy.
- Farm & Ranch: equipment type/make/minimum year/maximum hours/condition, plus
  pasture minimum acreage, water, fencing, and lease term.
- Livestock: species, breed, sale unit, and minimum head count.
- Home & Garden and Appliances: item type, brand, condition, and working
  status.
- Autos retains its established year/make/model/mileage controls and sorts.

Existing shared query behavior remains: state/county context and explicit
county scope, nearby county distance, full-text relevance, sort, pagination,
canonical/noindex metadata, fragment response, ordinary GET fallback, and
accessible mobile filter disclosure.

## Behavior and safety

The form builds a per-vertical allowlist. Fields for another vertical, fields
without a selected supported vertical, invalid values, `page`, and arbitrary
request keys are absent from the validated query object. They cannot create
ORM lookup paths and are not copied to filter chips, reset links, pagination,
or progressive-fragment URLs.

Filter application starts with the shared `public_listing_with_images()`
selector. Each parameter maps to a fixed typed-detail lookup. One-to-one
detail joins do not require `distinct()`; the pre-existing additional-county
scope join is the only browse path that uses it. PostgreSQL FTS relevance and
the bounded SQLite fallback compose before deterministic ordering.

Controlled Django model choices supply enum controls. Bounded text controls
are used for seller-entered typed make, brand, breed, item type, and lease
term; they are fixed case-insensitive lookups, not dynamic field names or
seller-defined taxonomies. Categories, controlled tags, seller tags, generic
profile attributes, and custom facts are not browse filters, per ADR-0023.

## Data, privacy, and security

There is no migration, index, data backfill, or new retained data. No index was
added because no representative `EXPLAIN (ANALYZE, BUFFERS)` evidence justified
one. Public filtering remains behind the centralized public selector, so
draft, review, suspended, sold, expired, inactive-location/category, and
otherwise non-public rows cannot surface through a typed join. Filters do not
read VIN, addresses, seller/contact information, moderation, billing, tags, or
custom facts.

## Accessibility and rollout

The server-rendered filter form groups shared and listing-detail fields in
native fieldsets. It remains open without JavaScript, while the established
mobile disclosure, labels, errors, focus behavior, live region, and ordinary
GET submit remain intact. The live enhancement requests the same validated
canonical query URL and only updates results after a successful fragment.

Rollback is an application/template/CSS/test/documentation revert. There is no
schema or data rollback.

## Tests and acceptance criteria

- Unit/route tests cover every typed filter group, public-selector composition,
  FTS query composition, and rejected cross-vertical/untrusted parameters.
- Existing scope, chip, reset, pagination, noindex/canonical, fragment, and
  Autos tests remain regression coverage.
- Playwright covers 390px Home, Rental, Farm & Ranch, and Home & Garden compact
  filter groups; the existing Autos live-filter test remains in the suite.
- `make check` and `make test-e2e` are the completion gates; exact outcomes are
  recorded in `VALIDATION.md`.
