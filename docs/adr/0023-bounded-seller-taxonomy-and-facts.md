# ADR 0023: Permit bounded seller tags and additional facts

- Status: Accepted
- Date: 2026-07-29

## Context

The catalog supplies the canonical vertical and primary leaf category that select a
listing workflow and canonical URL. Sellers also need a small way to describe a
listing when controlled catalog vocabulary is incomplete.

## Decision

Keep `Listing.category` as the sole primary controlled leaf and workflow input.
Sellers may add up to ten active controlled leaf tags in the same vertical and up to
ten plain-text seller tags (1–40 characters). Seller tags are normalized for
case/whitespace, stored in rows, unique per listing, and cannot duplicate controlled
tag labels.

Sellers may add at most eight flat label/value facts (label 1–60, value 1–500), stored
as rows and unique by normalized label per listing. This is the narrow exception to
ADR-0005: it is not an arbitrary EAV system. There is no schema nesting, type system,
files, joins used as filter definitions, arbitrary query API, or use in core
invariants.

All seller-defined text rejects markup, URLs, contact information, exact addresses,
coordinates, credentials, financial identifiers, reserved claims, and obvious
prohibited-policy terms. Validation is local and deterministic; no external automatic
moderation provider is called.

Controlled secondary tags and seller tags are included in public full-text search only
when the listing is published through the existing public selector. Custom facts never
enter FTS v1, browse filters, sorts, SEO, social metadata, or map input. Draft and
review values are visible only to the owner and authorized moderation staff, labelled
as pending publication. Approval/publish is the sole public gate; a material edit to
these values returns an active listing to review and immediately removes it from public
discovery.

If a seller fact becomes a recurring browse filter or sort, it must be promoted through
a new catalog/typed-field decision, migration, backfill/rollout plan, index review, and
feature specification. It must not be made filterable by querying these rows.

## Consequences

- `ListingCategoryTag`, `ListingSellerTag`, and `ListingCustomField` are additive,
  indexed/unique relational records. Existing listings retain no new rows and continue
  to derive their primary controlled category from `Listing.category`.
- Public search documents rebuild at publication; public status filtering prevents
  review data or stale text from surfacing.
- Non-goals: arbitrary tag filtering, custom-fact FTS/filter/sort, contact fields,
  automatic moderation, and provider integrations.

## 2026-07-30 clarification: Others overflow vertical

`Others` is a deliberately narrow overflow vertical, not a policy bypass. Its
single seed-owned `General` leaf remains the hidden canonical primary category
for workflow and URL stability. Sellers must supply at least one compliant
seller tag; after approval, `Others` plus those tags is the public
classification and the tags enter the existing public FTS path. The same
prohibited-content rules and human moderation gate apply before publication.
