# BIL-001 — Local Demo Billing Foundation

**Status:** Implemented locally; production provider incomplete  
**Milestone:** M6  
**Last updated:** 2026-07-23

## Problem and scope

M6 needs durable, server-priced orders and payment events without accepting a real
provider credential or production pricing policy. This slice supplies a
provider-neutral billing boundary with a deterministic local adapter only.

The local demo flow is available only with `DEBUG=True`: an eligible seller
submits an Autos fixed-price draft, which becomes `awaiting_payment`; checkout
creates a server-priced order; a staff-only local confirmation creates a durable
event; event processing marks the order paid and moves the listing to
`in_review`. Browser success and cancellation pages are informational only.

## Non-goals

No Stripe SDK/API/webhook, credentials, secrets, invoices, public featured
browse behavior, production fee, or production checkout is included. A staff
rejection of a paid local-demo listing creates one durable, idempotent full
refund event through the local adapter; production refunds still require the
future provider adapter.
The local $10.00 USD / 30-day configuration is demo data, not a production
pricing decision.

## Actors, data, and security

Sellers may create checkout only for their own `awaiting_payment` listing.
The server resolves `AUTOS_NEW_FIXED` and its effective `ProductPrice`; forms
accept no amount, currency, or product identity. Orders and order lines retain
immutable money/product/duration snapshots. `PaymentEvent` has a unique
`(provider, provider_event_id)` and is the compatible future replacement shape
for `StripeEvent`. Staff-only DEBUG confirmation is CSRF-protected and cannot
be invoked by a seller.

`FeaturedPlacement` is a non-exposed entitlement primitive. DEC-107 still
blocks any activation/start policy.

## Operations, migrations, and rollback

Apply `catalog.0006`, `listings.0010`, and `billing.0001`. In local DEBUG only,
run `python src/manage.py seed_texas_autos` then
`python src/manage.py seed_demo_billing`. The latter is idempotent and creates
the 1000-minor-unit USD row only after validating the Autos listing kind/mode.

Replay received/failed events with `python src/manage.py replay_payment_events`.
Disable local checkout by running non-DEBUG configuration; existing orders/events
remain auditable. Roll forward with a provider adapter rather than deleting
billing history.

## Acceptance tests

Tests cover server-owned pricing, ownership, browser-result non-payment,
DEBUG/staff confirmation guards, status/visibility behavior, payment mismatch,
duplicates/out-of-order events, and replay. No external payment service is
called.
