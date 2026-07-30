# LST-010 — Unified dynamic listing creation

**Status:** Implemented locally — production/launch eligibility remains pending  
**Authorization:** User-approved 2026-07-29  
**Scope:** One authenticated, full-page Create Listing workflow for every active catalog leaf.

## Problem and behavior

The previous dashboard exposed separate draft routes and a generic form. This feature
keeps those legacy routes compatible but makes `/dashboard/listings/new/` the single
obvious entry point. A seller selects a vertical, then a category group and leaf. A
group with children cannot be posted; a group without children (including `Other`) is
itself the postable leaf. The saved `Listing.category` is always that leaf.

A server-owned workflow resolver maps the selected leaf to one of the existing typed
detail workflows (Autos, Homes, Rentals, Agricultural Equipment, Livestock, Pasture,
Home & Garden, or Appliances) or to a catalog posting profile. Typed workflows keep
their existing one-to-one models, validation, private fields, services, and no generic
row. Catalog-profile workflows create only `GenericListingDetails`.

The page is ordinary server-rendered HTML. Its category selector and JSON endpoint
return only active postable leaves; active groups are never options, while childless
parents such as `Other` remain leaves. Each option includes vertical and, when present,
group context. JavaScript enhances the ordinary **Show fields** submission immediately
after leaf selection. Without JavaScript, the seller uses that control directly; the
server rerenders the same form with the selected workflow and preserves all
workflow-eligible values/errors without creating a draft. Generic placement, price,
private-address, and taxonomy/fact values remain bound; ineligible vertical values
are not carried into a typed or generic representation.
A stale or forged group ID receives the clear postable-subcategory error. A normal POST
never trusts a client workflow, profile version, field label, or schema.

The `Others` vertical is the sole exception to the visible-leaf selector: selecting it
server-resolves its hidden `General` leaf, so neither JavaScript nor no-JavaScript
sellers choose a meaningless category. An Others listing must include one compliant
seller tag; approved tags form its public classification and search terms. This narrow
overflow does not bypass prohibited-content rules or pre-publication moderation.

### Unified owner editing

`/dashboard/listings/<uuid>/edit/` is the single owner edit route for every
existing generic or typed listing. It resolves the persisted primary category and
workflow on the server; the primary category is displayed but cannot be changed
through this endpoint, so a request cannot switch a listing between typed and
generic representations. It loads and replaces the existing common fields,
actual typed or generic/profile values, eligible broker attribution, controlled
tags, seller tags, and custom facts. It never creates a generic row for a typed
listing or a typed row for a generic listing.

Only `draft`, `changes_requested`, and `published` owners can edit. The locked
service validates ownership and active-account status, preserves ZIP/county and
broker gates, and sends any published material edit to `in_review` immediately.
Draft and review taxonomy/facts remain owner/staff-only and are labelled pending;
the unified owner detail shows their current values without exposing private
values in public templates. Legacy direct create/edit/detail routes remain compatible
protected workflows; seller navigation and owner/public edit links use unified routes.

### Create-form refinement

Unified create and edit retain native state and county selects as the
server-rendered no-JavaScript controls. Authenticated JavaScript progressively
enhances them with bounded, keyboard-operable state/territory and state-scoped
county comboboxes. Candidates come only from active reference records; county
equivalents, including Alaska borough/census-area records, retain their imported
names. Selecting a location never submits the form. Changing state clears
incompatible placement after confirmation, while existing ZIP/county validation
remains authoritative.

Numbered essential sections and open native `details` elements group optional
category facts, tags, and eligible placement/address inputs. Optional controls
therefore remain visible and usable without JavaScript. Controlled-tag semantics,
seller-tag and custom-fact limits, broker eligibility, workflow selection, and
moderation behavior are unchanged.

## Data and schema

### Seller taxonomy and additional facts

ADR-0023 adds a narrow seller-authored extension to the unified flow. The seller
selects one top-level vertical and one primary postable leaf; that primary
`Listing.category` remains canonical for URLs, display, compatibility, and server-side
typed-workflow resolution. The existing category hierarchy is the controlled tag
source: a childless parent remains selectable, and optional additional active leaves
from the same vertical are stored as controlled tags. Neither additional controlled
tags nor arbitrary seller tags can choose a workflow.

Sellers can add at most ten 1–40-character plain-text tags and eight flat 1–60 /
1–500-character label/value facts. Both normalize whitespace/case for uniqueness and
reject markup, URLs, contact data, exact addresses, coordinates, credentials,
financial identifiers, reserved claims, and unsafe policy terms. They persist in
additive relational rows, not JSON. This is the ADR-0023 bounded exception to the
ADR-0005 no-EAV rule; facts are neither arbitrary schema nor queryable data.

Draft/review values are owner/staff-only and visibly pending approval. The existing
approval/publish transition makes controlled and seller tags public/searchable. Facts
become public only in a distinct Additional details section, and never participate in
FTS v1, filters, sorts, map, SEO, or social metadata. Edits to any of these values are
material and depublish a published listing into review.

`CatalogPostingProfile` and `CatalogPostingField` are controlled catalog records,
seeded from a versioned declarative source. A field has an allowlisted primitive type,
label, requiredness, choices, public/owner/staff visibility, display order, maximum
length/value, material-edit flag, and explicit public-search flag. Profiles are
attached to categories and are never arbitrary seller-defined schemas.

`GenericListingDetails.attributes` is one bounded flat JSON object and
`schema_version` identifies the applied profile version. It is only for profile
supplemental facts; price, location, lifecycle, and common listing fields remain typed
columns. Validation permits at most 16 keys, 8 KiB encoded data, depth 1, 240-character
text values, booleans, bounded integers, and configured choices. Unknown, stale, nested,
HTML/file/contact/exact-address/coordinate keys or values are rejected. This narrow,
infrequently queried extension metadata complies with ADR-0005; an ADR supersession is
not needed because it is not EAV and is not used for filters, sorts, or core invariants.

The additive migrations require no backfill. Existing generic rows receive the model
defaults and remain readable. Rollback is application rollback plus a forward fix; do
not remove populated profile or attribute data.

### Approved broker attribution

Homes, Rentals, and all Farm & Ranch leaf workflows may collect one optional,
normalized public `Listing.broker_name` (120 characters). The form label is
**Broker or brokerage** and accepts a company or broker name only; it does not
collect a person profile, phone number, email address, license number,
verification state, or contact link. The server resolves the listing category
before accepting the value and rejects forged broker input for every other
vertical. Existing typed routes use the same rule.

Broker attribution is material listing data: a published edit follows the
existing re-moderation transition. It is rendered only as a public fact for an
eligible published listing. It is deliberately excluded from map queries,
public FTS, social metadata, staff/policy claims, filters, and indexes.

## Privacy, search, and lifecycle

Templates escape all values. Public presenters show only fields marked public; owner and
staff-only facts do not enter public templates, metadata, or maps. Only explicit
public-search fields are added to the existing public FTS document and SQLite fallback.
There are no JSON browse filters, JSON indexes, arbitrary JSON queries, files, or
contact/address collection in v1. Owner checks, active-account checks, CSRF, and the
existing ZIP/FIPS/county rules continue to apply.

Changing structured values is a material edit. The existing locked update service moves
a published listing to `in_review`, records the material-edit moderation action, and
rebuilds public search only after approval.

## Seed, rollout, and operations

The idempotent catalog seed upserts known profiles/fields by category and stable field
key, restores only seed-owned values, and never deletes unknown historical profile data
or values. `make seed-marketplace-catalog` and `make seed-demo-full` run it. Catalog
profile v2 uses reusable safe-fact archetypes for every generic leaf: condition,
brand/make/model, size/dimensions, color/material, age/year, quantity,
compatibility/fit, service/job availability, and pickup/delivery are selected where
meaningful. Typed leaves use their existing detail forms only and have inactive
historical profiles rather than JSON fields. No profile adds contact, exact-address,
financial, medical, veterinary, or regulated claims.

`make seed-demo-generic-taxonomy` supplies bounded DEBUG-only public evidence for
ADR-0023 without assigning taxonomy/facts to typed records. It publishes six
synthetic generic examples (Services, Business & Industrial, Jobs, Collectibles
& Art, Electronics, and Others) through the existing demo approval service. Each
uses a primary leaf, seller tag, and safe custom fact; all but Others also use a
same-vertical controlled tag. Others uses its only hidden `General` leaf. Pets and
Home & Garden remain excluded because their current workflow resolution is typed.
The fixture is idempotent and never deletes or updates user-owned records.

Deploy additive migrations first, then code, then run the catalog seed. Rebuild public
search documents after enabling profiles for already-published generic rows. Existing
typed and generic URLs continue to work.

## Non-goals

This does not add payment products, messaging, ratings, contact sharing, exact address
entry in profiles, JSON filters/sorts/indexes, EAV, bulk feeds, or production-policy
approval for catalog content. Existing prohibited-content review remains mandatory.
It also does not add arbitrary tag filters, custom-fact FTS/filter/sort, automatic
moderation, or provider integrations.

## Verification plan

- Resolver tests cover every typed workflow and generic fallback.
- Profile/model/form tests cover required fields, choices, unknown/stale keys, type and
  size limits, visibility, search inclusion, and material edits.
- Route tests cover authentication, owner authorization, CSRF, no-JS group/leaf
  validation, generic and typed creates, and non-overlapping detail rows.
- Seed tests prove idempotency and preservation of unknown historical profile records.
- Playwright covers Home and a catalog-only listing, plus a 390px narrow check.
- Run migration check, inspect `sqlmigrate`, `make check`, and `make test-e2e`.
