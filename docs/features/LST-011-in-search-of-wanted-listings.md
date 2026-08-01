# LST-011 — In Search Of / Wanted listings

**Status:** Implemented locally  
**Authorization:** User-approved 2026-07-31

## Behavior

`Listing.intent` is an additive, persisted `offer`/`wanted` distinction. Existing
rows default to `offer`. A wanted post keeps its selected existing `vertical` and
postable-leaf `category` as the target classification; the catalog does not contain
a cross-vertical Wanted vertical.

Wanted posts use `GenericListingDetails` only, even when their target category would
normally resolve to a typed sale workflow. The seller enters a title, description,
target vertical/category, city/state/county/ZIP, optional broker attribution where
the target category permits it, approved tags/facts, and either an optional USD
budget or **Contact with offer**. Typed sale fields and listing kinds are rejected.
Category selection uses the existing non-persistent Show fields/no-JavaScript
advance contract.

The seller can create a wanted post from `/dashboard/listings/wanted/new/`. Public
cards and details label it “Wanted” and “In Search Of” in text. `/in-search-of/`
is a dedicated directory and reuses the public selector, state/county scope,
vertical/category filters, pagination, fragment behavior, and noindex query policy.
Normal state/county browse defaults to offers, preserving its existing behavior;
the allowlisted Listing type control explicitly chooses Wanted or All.

## Lifecycle, privacy, and moderation

Wanted rows reuse draft/submission/review/approval/rejection/changes-requested,
reports, favorites, media, map privacy, audit, and material-edit re-review.
Public visibility remains exclusively behind `public_listings()`. Search documents
include only public title, description, target category/vertical, approved tags,
and the public intent label; no private data is added.

The accepted temporary policy is that Wanted posts honor the selected target
category's existing media requirement and have no expiration until a later accepted
policy defines one. There is no payment, production pricing, messaging, ratings, or
automatic matching/alerts.

## Migration and rollout

`listings.0019_listing_intent` adds the non-null field with database default
`offer`, an intent check constraint, and a deliberate public intent/state ordering
index. It performs no Python backfill or destructive operation. Deploy migration
before application code; rollback traffic first and retain populated intent data for
a forward fix.

## Verification

Tests cover default intent, generic-only wanted creation against a typed target,
optional budget/contact wording, non-validating advance, moderation/public
visibility, explicit browse separation, and favorite/report reuse. Run migration
checks, inspect generated SQL, focused tests, `make check`, and `make test-e2e`
before release; record only executed commands in `VALIDATION.md`.
