# LST-008 — Seller Management, Favorites, and Renewal

**Status:** Implementing  
**Milestone:** M8  
**Last updated:** 2026-07-23

## Problem and scope

Owners need safe self-service after publication and buyers need private saved
listings. This slice introduces grouped seller inventory, immutable lifecycle
actions, favorites, expiration-safe visibility, material-edit re-review, and a
local-demo-compatible renewal order boundary.

## Non-goals

No scheduled expiration command (M9), real Stripe, refunds, CDN changes,
messages, notifications, or production price constants are included.

## Actors, permissions, and behavior

- Authenticated listing owners can mark a published listing sold, archive eligible
  private/closed listings, and restore an archived listing to draft. No hard
  delete path exists.
- Seller writes to material fields or images on a published listing transition it
  to `in_review` in the same transaction. Draft editing remains available.
- Public queries exclude non-published, inactive-reference, and expired rows even
  if their stored status has not yet been moved to `expired`.
- Authenticated users may toggle a favorite only for a row from the centralized
  public selector. Favorites lists use that selector again, so a subsequently
  private, sold, archived, or expired listing is not disclosed.
- Renewal creates a new server-priced order from an active renewal catalog
  product. One pending renewal is unique per listing. A verified/local approved
  payment restores only an unchanged listing within the seven-day grace period;
  the new expiry uses the immutable order-line duration snapshot.

## State, security, and migration

`sold`, `expired`, and `archived` are additive lifecycle states. `expires_at` and
`last_material_edit_at` support visibility and renewal decisions. `Favorite` has
a unique `(user, listing)` constraint. `Order.purpose` and its partial unique
pending-renewal constraint prevent duplicate payment requests from granting
duplicate entitlements. All browser mutations are POST and CSRF-protected;
services enforce ownership or public visibility under row locks.

Apply `listings.0011` and `billing.0002`. Review the generated PostgreSQL SQL
before release. Roll back by disabling routes/application behavior; retain the
additive audit, favorites, and financial records for a forward fix.

## Acceptance coverage

Service and web tests cover owner/other/anonymous actions, expiration selector
safety, material depublishing, favorite privacy/toggle, and renewal
idempotency/grace boundaries. The local $10 demo remains DEBUG-only and is not a
production amount or pricing decision.
