# ADR-0014: Local deterministic billing adapter

**Status:** Superseded in part by ADR-0025
**Date:** 2026-07-23

## Context

M6 requires a payment-to-moderation boundary, but no Stripe account, credentials,
or production price is authorized. A browser redirect cannot establish payment
truth.

## Decision

Use a DEBUG-only `local_demo` adapter. It creates durable, uniquely identified
provider-neutral payment events, which are processed by the same idempotent
handler used by replay. Only a Django staff user may create the deterministic
local success event. The event validates the immutable order amount/currency
before marking an order paid and publishing the listing after moderator approval.

ADR-0025 replaces the original pre-moderation payment sequence and Autos-only
demo price. The local command now configures the approved all-catalog
primary/additional-county demo pricing. The future Stripe adapter will persist
`StripeEvent` records using this event contract and will add raw-body signature
verification without changing order truth rules.

## Consequences

Production remains unable to collect payments until a reviewed Stripe adapter and
configuration are approved. Browser status pages remain safe. The model retains
order, line, event, and entitlement audit data while DEC-004 and DEC-107 remain
unresolved.
