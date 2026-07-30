# Feature Specification: LST-004 — Home Goods Private Drafts

**Status:** Implemented locally; later public-demo slice supersedes prior
private-only boundary  
**Owner:** Project owner  
**Milestone:** M3  
**Last updated:** 2026-07-23  

> Historical scope note: this draft slice excluded public Home Goods pages. The
> later nationwide demo-inventory/public-detail work presents controlled Home &
> Garden and Appliances examples; it does not add non-demo seller submission,
> products, or pricing.
**Authorization:** User-authorized implementation

## Problem and outcome

Sellers need structured private drafts for the existing Appliances and Home &
Garden catalog verticals before listing policy, pricing, submission,
moderation, media, or public visibility is approved. Authenticated sellers can
create, inspect, and edit only their own drafts.

## Scope

- Add one typed `HomeGoodsDetails` one-to-one Listing detail model for the
  explicitly allowed `appliances` and `home-garden` vertical slugs.
- Record item type/category, optional brand and dimensions, condition, working
  status, and pickup/delivery preference.
- Add separate fixed-vertical transactional create/update services, owner
  selectors, authenticated dashboard routes, forms, private templates, and a
  bounded DEBUG-only local seed.

## Non-goals

- Dangerous/prohibited category policy, product/listing-kind eligibility,
  prices, submission, moderation, payments, media, public selectors,
  browse/detail pages, or search.
- Public publication of Appliances or Home & Garden inventory.

## Behavior and data rules

- `item_type` is required and must not be whitespace-only. Brand and dimensions
  are optional. Condition, working status, and fulfillment preference are
  controlled enums.
- Forms never include Listing vertical or status. Separate services supply the
  fixed active Appliances or Home & Garden vertical. Update services lock the
  listing, enforce ownership and draft status, and reject a mismatched vertical.
- PostgreSQL triggers reject direct Home Goods detail writes for unsupported
  verticals and reject switching a listing with Home Goods details to an
  unsupported vertical. Django model validation provides the same compatible
  vertical boundary under SQLite.

## Security, privacy, and errors

- All routes require authentication; non-owner and non-draft reads return 404.
- Browser writes use CSRF-protected POSTs. Templates are private dashboard
  surfaces only.
- No public selector, template, URL, media upload, external call, or sensitive
  logging is introduced.

## Migrations, rollout, and rollback

The additive migration creates the detail table and PostgreSQL trigger
functions. Apply it before the local seed. Rollback is a forward correction:
drafts stay private and affected catalog references may be deactivated; owned
draft data is not deleted.

## Development seed

`seed_demo_home_goods_drafts` is DEBUG-only and requires existing local demo
seller accounts, active locations, and existing Appliances/Home & Garden
categories. It idempotently creates exactly one private draft for each
supported vertical and never publishes or changes an existing draft.

## Tests and acceptance criteria

- Tests cover model validation, fixed verticals, ownership, draft-only
  services, anonymous redirects, owner 404s, vertical/status tampering, and
  idempotent seeding.
- PostgreSQL tests cover incompatible direct detail writes and incompatible
  listing vertical switches.
- Existing Autos, property, rural, and public Autos browse behavior remains
  unchanged.
