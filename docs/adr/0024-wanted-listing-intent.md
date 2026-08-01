# ADR-0024: Wanted posts are a listing intent

**Status:** Accepted 2026-07-31

## Decision

Model In Search Of / Wanted as `Listing.intent`, with `offer` as the default and
`wanted` as the approved additional value. A wanted row's existing `vertical` and
`category` identify what it seeks. Do not create a literal Wanted catalog vertical
or cross-vertical categories because `Listing.category` must remain in
`Listing.vertical`.

Wanted uses the existing generic-details representation and never a typed
sale-detail model or sale listing kind. It may target any active postable leaf.
Existing shared lifecycle, moderation, media, location, taxonomy, broker
eligibility, reporting, favorites, privacy, and public selector boundaries apply.

## Temporary policy

Wanted listings honor the selected target category's current media requirement and
have no expiration until a subsequent accepted product policy defines one.

## Consequences

Browse defaults to offers and exposes a bounded intent filter; the dedicated
In Search Of directory defaults to wanted. Search intent is visible rather than
silently mixing wanted and sale results. The additive migration defaults historic
rows to offers and retains data on rollback for a forward fix.

This ADR does not add messaging, payments, production pricing, ratings, automatic
matching/alerts, or a new catalog hierarchy.
