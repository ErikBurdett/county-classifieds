# Feature Specification: CAT-004 — Marketplace Taxonomy Catalog Expansion

**Status:** Implemented locally; posting-profile extension delivered by LST-010  
**Owner:** Project owner  
**Milestone:** M2  
**Last updated:** 2026-07-29  
**Authorization:** User-authorized implementation

## Problem

The marketplace needs a durable, recognizable browse taxonomy before future
vertical slices are designed. Existing Autos reference data must remain
compatible while the catalog can describe the broader regional marketplace.

## Scope

- Versioned, declarative reference data for 19 controlled marketplace
  verticals and their parent/child categories.
- A DEBUG-only, idempotent `seed_marketplace_catalog` command and Make target.
- Active vertical/category records, stable display order, generic `Other`
  category groups, and admin navigation support.
- Postable-leaf selector support for LST-010: active groups with children are
  browse context only, while childless parents remain postable leaves.
- Existing Autos URL slugs remain active and compatible.
- Others is a narrow generic overflow vertical with one hidden internal `General`
  leaf; seller tags provide its public classification after moderation approval.

## Non-goals

- Seller-facing category browsing or posting UI. (Posting is superseded by LST-010.)
- Listing models, forms, routes, `ListingKind` records, products, price modes,
  prices, or policy approval for non-Autos verticals.
- A prohibited-items policy. Pets are catalog vocabulary under Livestock &
  Animals only; this does not approve pet listings.

## Actors and permissions

| Actor | Permission |
|---|---|
| Seller/browser | None; catalog records do not grant posting eligibility. |
| Django staff with catalog permissions | View and manage catalog records through standard Django admin permissions. |
| Local developer/operator | Run the DEBUG-only seed command. |

## Behavior and data rules

- The catalog contains Autos & Vehicles, Real Estate, Rentals, Farm & Ranch,
  Livestock & Animals, Home & Garden, Appliances, Electronics, Tools &
  Equipment, Business & Industrial, Sporting & Outdoor, Recreation & Hobbies,
  Clothing & Personal, Collectibles & Art, Kids & Baby, Jobs, Services, and
  Community, plus Others.
- Categories use only one parent level and every parent belongs to the same
  vertical, matching the existing model and database trigger.
- Each seed-owned record is identified by vertical slug or `(vertical slug,
  category slug)`. Re-runs update only its controlled fields and never delete
  records. Other staff-created records are untouched.
- `autos` and its established `cars`, `trucks`, `suvs`, `vans`, `motorcycles`,
  and `other-autos` category slugs are retained and activated.
- Listing readiness is descriptive code metadata, not an authorization
  mechanism. Autos alone has a `ListingKind`, products, and local billing
  configuration. Eight typed presentations now exist for controlled local demo
  inventory; this does not grant non-Autos seller posting eligibility.
  Community, Jobs, and Services are catalog-only and have no listing products.

## Errors, security, and privacy

The command refuses non-DEBUG settings. It creates no public route, seller
input, listing data, payment data, or policy exception. Admin receives only
navigation configuration; no action bypasses existing restrictions.

## Migrations, rollout, and rollback

No migration is required because the existing vertical/category schema and
same-vertical parent trigger already support the hierarchy. Deploy the code,
then run the command only in a DEBUG local environment. Roll back with a
forward correction to the declarative seed or by deactivating records; never
delete taxonomy records referenced by listings.

## Tests and acceptance criteria

- Re-running the command creates no duplicates and reports unchanged records.
- All expected verticals and categories are active, one level deep, and
  parented within the same vertical.
- Existing Autos seed URLs remain active.
- The command creates no non-Autos `ListingKind` or product records.
- Active group records are excluded from seller posting selectors and endpoints;
  leaf labels retain vertical/group context.
- No catalog group contains firearms, controlled substances, adult services,
  or financial/crypto categories.
- Others remains subject to the same prohibited-content and moderation policy; it
  does not authorize otherwise prohibited listings.

Acceptance is met when the expanded catalog is available as controlled
reference data while ListingKind plus typed vertical slices remain the sole
posting gate.
