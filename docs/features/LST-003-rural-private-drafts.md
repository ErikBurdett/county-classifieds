# Feature Specification: LST-003 — Rural Private Drafts

**Status:** Implemented locally; later public-demo slice supersedes prior
private-only boundary  
**Owner:** Project owner  
**Milestone:** M3  
**Last updated:** 2026-07-23  

> Historical scope note: this draft slice excluded public rural pages. The
> later nationwide demo-inventory/public-detail work presents controlled rural
> examples; it does not add non-demo seller submission, products, or pricing.
**Authorization:** User-authorized implementation

## Problem and outcome

Sellers need structured private drafts for Agricultural Equipment, Livestock,
and Pasture before any listing policy, pricing, submission, moderation, media,
or public visibility is approved. Authenticated sellers can create, inspect,
and edit only their own drafts.

## Scope

- Add `AgEquipmentDetails`, `LivestockDetails`, and `PastureDetails` one-to-one
  detail models.
- Use the existing catalog slugs: `farm-ranch` for Agricultural Equipment and
  Pasture, and `livestock-animals` for Livestock. Listing categories remain the
  controlled existing categories under those verticals.
- Add fixed-vertical transactional create/update services, owner-scoped
  selectors, authenticated dashboard routes, forms, private templates, and a
  bounded DEBUG-only local seed.
- Record only common Listing city, county, and general description alongside
  the typed facts.

## Non-goals

- ListingKinds, products, prices, seller submission, moderation, payments,
  media, public selectors, browse/detail pages, or public search.
- Health or testing information, animal registration IDs, serial numbers,
  exact property addresses, or other policy-sensitive collection.

## Behavior and data rules

- Agricultural Equipment records type, optional make/model/year/hours, powered
  state, and condition.
- Livestock records species, optional breed/class/age-or-weight text, positive
  head count, and controlled sale unit. Age-or-weight is general descriptive
  text only, never health/testing or registration data.
- Pasture records positive decimal acreage, water/fencing booleans, lease term,
  optional use restrictions, and availability date. It has no address field.
- Forms never include Listing vertical or status. Services supply the fixed
  active vertical and updates lock the listing, enforce owner and draft status,
  and reject a mismatched vertical.
- PostgreSQL triggers reject direct detail inserts/updates for incompatible
  verticals and prevent a listing vertical switch after any rural typed detail
  exists. Django model validation provides the equivalent boundary under
  SQLite.

## Security, privacy, and errors

- All routes require authentication; non-owner and non-draft reads return 404.
- Browser writes use CSRF-protected POSTs. Templates are private dashboard
  surfaces only.
- No rural public selector, template, URL, media upload, external call, or
  sensitive logging is introduced.

## Migrations, rollout, and rollback

The additive migration creates the three detail tables, typed check
constraints, and PostgreSQL trigger functions. Apply it before the local seed.
Rollback is a forward correction: drafts stay private and the affected catalog
records may be deactivated; seller-owned draft data is not deleted.

## Development seed

`seed_demo_rural_drafts` is DEBUG-only and requires existing local demo seller
accounts, active locations, and the existing Farm & Ranch/Livestock catalog
categories. It idempotently creates exactly one private Agricultural Equipment,
Livestock, and Pasture draft and never publishes or changes an existing draft.

## Tests and acceptance criteria

- Tests cover model/form validation, fixed verticals, ownership, draft-only
  services, anonymous redirects, owner 404s, and vertical/status tampering.
- PostgreSQL tests cover incompatible direct rural detail writes and unsafe
  listing vertical switches.
- Seed reruns create no duplicate drafts and never publish them.
- Existing Autos, Homes, Rentals, and public Autos browse behavior remains
  unchanged.
