# Feature Specification: SRCH-003 — PostgreSQL Full-Text Search

**Status:** Implemented locally — representative production query-plan evidence pending  
**Milestones:** M7 public browse; M10 progressive browse UX  
**Last updated:** 2026-07-29

## Problem and scope

Buyers need bounded text search without introducing a provider, a SPA, typo
search, or a ranking policy for featured listings. Search is available on public
state and county browse routes and always starts from `public_listings()`;
drafts, expired/suspended/sold listings, inactive catalog/location references,
and stale documents cannot surface.

The county URL is context, not an implicit filter. A county route defaults to
`scope=state` (including an omitted or invalid scope), therefore searches its
statewide inventory. `scope=county` limits results to primary county and
additional county placements, with `distinct()` preventing duplicates. State
pages remain statewide and do not render a scope control. Scope is preserved in
validated pagination, live-fragment URLs, filter chips, reset links, and the
no-JS GET form. Invalid scope is discarded rather than copied into a chip or
canonical query.

## Data and privacy

`Listing.search_document` is a nullable PostgreSQL `SearchVectorField`, using
the `english` configuration and a GIN index. The document uses A: title; B:
active category/vertical labels and approved typed descriptors (Autos
make/model/trim; equipment make/model/type; Home Goods brand/item type;
livestock species/breed/class; Home/Rental type labels; pasture acreage,
water/fenced/lease terms); C: city; D: description.

It never includes VIN, street/unit/postal addresses, `general_area`,
coordinates, seller/contact data, photo filenames/keys, internal moderation,
billing, or other private aggregate data. Rebuild code has a single allowlist
API (`apps.listings.search`) and publication/moderation services rebuild before
the public transaction commits. Material edits move published rows out of the
shared selector, so a stale document cannot disclose an edit.

## Query behavior

PostgreSQL parses nonblank `q` with `SearchQuery(..., search_type="websearch",
config="english")`, filters the persisted vector, and orders `SearchRank`
descending followed by the requested deterministic sort. Blank and malformed
websearch input safely returns no FTS condition/no server error. No raw request
text ever becomes an ORM lookup path. SQLite uses a bounded, public-safe
`icontains` fallback across the same practical listing/category/typed browse
labels; it does not import or execute PostgreSQL SQL.

There is no featured/rank boost: DEC-107 remains unresolved. There is no
trigram, unaccent, OpenSearch, provider integration, or radius search.

## Migration, rollout, and rollback

Migration `0014` adds a nullable column (no table-wide backfill), creates the
GIN index only on PostgreSQL, and adds the deliberate additional-placement
county index. SQLite runs the schema state safely without PostgreSQL index SQL.
Deploy schema first, then run `make rebuild-listing-search-documents` in bounded
idempotent UUID-ordered batches (for example
`EXTRA_ARGS="--batch-size 250 --max-batches 20"`), then enable/use browse
behavior. New publications populate their own document.

Rollback is application-first: revert traffic to the bounded fallback while
retaining the additive column/index. A forward migration may remove them only
after an approved retention/deployment review. The command can resume safely
because every batch regenerates full documents.

## Performance, observability, and tests

The only new indexes are the GIN document and
`ListingCountyPlacement(county)`. Operators must capture
`EXPLAIN (ANALYZE, BUFFERS)` for a representative state and county query after
the nationwide seed and document rebuild:

```bash
uv run python src/manage.py shell -c 'from apps.listings.models import Listing; print(Listing.objects.filter(search_document__search="tractor").explain(analyze=True, buffers=True))'
```

Do not treat timing from an empty/small database as production evidence. Tests
cover PostgreSQL document weights/query/rank/privacy/index behavior where a
PostgreSQL test database is configured, SQLite fallback, scope and fragments,
and browser query preservation. Query-count assertions use budgets rather than
exact counts; plan shape is documented from operator evidence.

The rebuild command hydrates controlled category tags, seller tags, generic
details, a generic category's posting profile/fields, and the existing typed
details once per UUID-ordered batch. This avoids per-listing relation queries
while preserving the document allowlist, weights, ranking, and batch semantics.

### Recorded local evidence (2026-07-29)

After applying `0014` and rebuilding 25,792 locally seeded documents, a broad
`Demo Auto` FTS query returned 3,234 rows in 18.011 ms (`EXPLAIN ANALYZE,
BUFFERS`; 1,505 shared-buffer hits). PostgreSQL selected a sequential scan
because that broad term matched about 12.5% of the fixture; this is expected
cost-based behavior, not evidence that the GIN index is absent. Operators
should repeat with representative selective terms and the full public selector
when production inventory is available before adding any more indexes.

## Acceptance criteria

- Public search has deterministic relevance-first ordering and no private text.
- County scope defaults statewide; explicit county scope includes both placements.
- Backfill is explicit, bounded, and idempotent; migrations do no unbounded work.
- Search/filter URL state remains safe for server and progressive-enhancement use.
