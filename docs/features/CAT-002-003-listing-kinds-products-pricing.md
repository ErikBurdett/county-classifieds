# Feature Specification: CAT-002/003 — Listing Kinds, Products, and Effective Pricing

**Status:** Accepted / implementing  
**Owner:** Project owner  
**Milestone:** M2  
**Last updated:** 2026-07-23  
**Authorization:** User-authorized implementation

## Problem

Listing eligibility and prices must be controlled by the marketplace, not
seller-submitted fields or browser input. The catalog needs an explicit model
for vertical-specific listing kinds, price modes, product use cases, and prices
that vary over time.

## Scope

- `ListingKind` belongs to one catalog vertical and has an active state.
- Normalized `ListingKindPriceMode` rows define each kind's supported seller
  price modes.
- `ListingProduct` has a globally unique, immutable product code, listing kind,
  active state, use case (`new_listing` or `renewal`), price mode, and explicit
  free-product state.
- `ProductPrice` stores ISO currency, nonnegative integer minor-unit amount,
  and `[effective_from, effective_until)` time windows.
- Catalog selectors/services resolve an eligible product and exactly one
  effective price at a supplied timezone-aware timestamp.
- Django admin manages catalog records with protected deletion, immutable
  product codes, and immutable existing price rows.
- The existing DEBUG-only Texas/Autos seed additively creates an Automobile
  kind, fixed/negotiable/contact modes, and fixed/contact new-listing product
  examples without price rows.

## Non-goals

- Seller-editable product, pricing, or price-mode fields.
- Changes to the existing private Autos draft model, form, routes, or UI.
- Checkout, orders, Stripe mappings, payment collection, invoices, renewals,
  entitlements, publication, or public browse/search behavior.
- Approved dollar amounts. Operators must add reviewed prices through admin or
  a later controlled catalog import.

## Actors and permissions

| Actor | Permission |
|---|---|
| Seller/browser | None; no catalog UI or input is exposed. |
| Django staff with catalog permissions | Create catalog records and append new effective prices. |
| Catalog service | Resolve only active, supported server-owned products and prices. |

## Behavior and data rules

- DEC-103 accepts Autos fixed, negotiable, and contact-for-price modes; Autos
  does not support free.
- A product is eligible only when its listing kind, vertical, and product are
  active; its use case and price mode must match the supplied context; and that
  price mode is supported by the kind.
- A free product has only zero price rows. A non-free product has no zero price
  rows. Autos products cannot be free or have a zero price.
- Currency must be an uppercase three-letter ISO code. Amounts are integer
  minor units and may not be negative.
- The effective window starts inclusively and ends exclusively. A null end is
  open-ended. Windows must have a positive duration.
- PostgreSQL excludes overlapping price windows for the same product/currency;
  therefore a valid catalog has at most one effective price at any timestamp.
- Resolver services reject inactive/unsupported products, no price, and
  ambiguous price data with domain errors. They require timezone-aware input.

## Errors and observability

Catalog resolution exposes `ProductNotEligibleError`, `NoEffectivePriceError`,
and `AmbiguousEffectivePriceError`; callers must not substitute a browser price
or silently choose a row. This slice adds no public endpoint, metrics, or
sensitive logging. Staff should correct invalid catalog data through controlled
admin records and normal database migration procedures.

## Security and privacy

No seller data, payment data, or public API is introduced. Server-side services
accept only catalog IDs/codes and timestamps, and never trust seller-provided
amounts. Admin uses Django's existing staff permission model; historical
catalog definitions and prices are protected from deletion in this slice.

## Migration, rollout, and rollback

The migrations are additive: they create catalog tables, indexes, check/unique
constraints, and PostgreSQL-only `btree_gist` exclusion/trigger protections.
SQLite development tests retain model and service validation; CI uses PostgreSQL
to validate the exclusion constraint and triggers.

Deploy migrations before running the existing development seed. The seed is
idempotent and adds no price rows. Rollback is a forward fix: deactivate
products/kinds or append a replacement effective price. Do not delete price
history or rewrite product codes.

## Tests and acceptance criteria

- Model tests reject an unsupported product mode, free Autos product, zero
  non-free price, invalid windows, and invalid currency/amount combinations.
- Service tests resolve a current eligible product/price and fail closed for
  inactive kind/product, unsupported mode, no price, ambiguous data, and naive
  timestamps.
- PostgreSQL tests verify overlapping same-product/currency windows and a zero
  non-free direct write are rejected by database protections.
- Seed tests verify re-runs preserve a single Autos kind, its three accepted
  modes, and fixed/contact product examples without encoded amounts.
- Existing Autos draft workflow tests remain unchanged and green.

Acceptance is met when the catalog independently owns eligibility and
effective-dated pricing without changing any seller-facing listing behavior.
