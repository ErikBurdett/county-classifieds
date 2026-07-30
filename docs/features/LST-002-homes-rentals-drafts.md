# Feature Specification: LST-002 — Homes and Rentals Private Drafts

**Status:** Implemented locally; later public-demo slice supersedes prior
private-only boundary  
**Owner:** Project owner  
**Milestone:** M3  
**Last updated:** 2026-07-23  

> Historical scope note: this draft slice intentionally excluded public
> property pages. The later nationwide demo-inventory/public-detail work now
> presents controlled Home and Rental examples using general-area data only;
> it does not add non-demo seller publication or expose exact addresses.
**Authorization:** User-authorized implementation

## Problem and outcome

Homes and rental inventory needs structured, privacy-preserving seller drafts
before it can be submitted, moderated, priced, or published. Authenticated
sellers can create, edit, and inspect only their own private Home or Rental
drafts. Exact property addresses are collected separately from the listing
city and remain private by default.

## Scope

- Add one-to-one `HomeDetails` for the `real-estate` vertical and
  `RentalDetails` for the `rentals` vertical.
- Add separate transactional create/update services, owner-scoped selectors,
  authenticated dashboard routes, forms, and private templates for each
  vertical.
- Capture typed property/rental facts, private exact-address fields, general
  area, and an explicit `exact_address_public` opt-in defaulting to false.
- Add PostgreSQL trigger protections against incompatible detail rows and
  changing a listing vertical after a typed detail exists.

## Non-goals

- Seller submission, publication, moderation, payment, listing media, public
  property browse/detail routes, property search, or a public property
  selector.
- New listing kinds, products, prices, public display policy, or nationwide
  inventory rollout. Existing Autos behavior and public browse remain
  unchanged.

## Actors and permissions

| Actor | Permission |
|---|---|
| Authenticated seller | Create, read, and update only their own draft Homes and Rentals listings |
| Anonymous user | Redirected to sign-in for private routes |
| Other seller | Receives 404 for a private draft |
| Django staff | Standard Django admin permissions only |

## Behavior and data rules

- Home property types are house, condo, townhouse, manufactured home, land,
  multifamily, commercial, and other. Rental types are apartment, house,
  townhouse, room, manufactured home, vacation, commercial, storage, and
  other.
- Prices remain on the shared Listing's existing minor-unit/currency fields.
  Rental monthly rent and security deposit use non-negative integer minor
  units.
- Beds are non-negative whole numbers, baths and lot sizes use decimals,
  square footage/year built are non-negative whole numbers, and lot size has
  an explicit acres or square-feet unit. Land, commercial, and other Homes
  may omit beds, baths, and square footage; storage, commercial, vacation, and
  other Rentals may omit beds and baths.
- Rental lease term is either a positive number of months or explicitly
  flexible. Pets policy is a controlled enum.
- Private exact address fields are normalized. A seller may elect public
  display only after supplying a street address. The opt-in remains false by
  default.
- Creation and update services lock the listing on update, enforce ownership
  and draft-only state, and use the corresponding fixed vertical; no generic
  cross-vertical service is introduced.

## Security, privacy, and errors

- All routes are authenticated; owner-scoped reads return 404 for non-owners
  and non-drafts. Browser writes are CSRF-protected POST requests.
- The owner detail view may show the exact address. There is no public
  property template or selector. Any future public template must render the
  exact address only when `exact_address_public` is true.
- Form failures show a summary and per-field errors. Direct model/service
  validation remains active for SQLite; PostgreSQL triggers preserve
  cross-table vertical compatibility against direct writes and races.
- No property address is placed in URLs, logs, analytics, or seed output.

## Observability

This private slice adds no external calls, background jobs, analytics, or
sensitive logging.

## Migrations, rollout, and rollback

The additive migration creates typed detail tables, non-negative/check
constraints, and PostgreSQL-only trigger functions. It updates the existing
listing relation trigger to protect all typed detail associations. Apply schema
before enabling the development seed. Rollback is a forward fix: leave drafts
private and disable their categories/verticals; do not delete seller-owned
address data.

## Development seed

`seed_demo_properties` is DEBUG-only and idempotently creates a small number
of private Home and Rental drafts for existing local demo seller accounts. It
does not alter or publish existing drafts. Nationwide publication waits for M5
submission/moderation and M7 public visibility/search policy; the local seed
is not launch inventory.

## Tests and acceptance criteria

- Model/form/service tests cover typed and conditional validation, privacy
  defaults, correct verticals, non-negative values, locks/ownership, and
  draft-only updates.
- Request tests cover anonymous redirects, owner access, other-seller 404,
  create/edit, form errors, dashboard links, and owner-only exact-address
  display.
- PostgreSQL migration tests cover incompatible typed rows and direct listing
  vertical changes. At the time of this private-draft slice, tests verified no
  public property route or selector; later controlled demo presentation is
  documented above.

Acceptance for this private-draft slice is met when sellers can manage only
their own typed Home and Rental drafts, with exact addresses private by default.
property surface.
