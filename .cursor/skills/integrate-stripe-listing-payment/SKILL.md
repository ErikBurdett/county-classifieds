---
name: integrate-stripe-listing-payment
description: Implement Stripe Checkout and webhook-backed listing-fee or featured-upgrade entitlements safely.
argument-hint: "<accepted payment feature spec>"
disable-model-invocation: true
---

# Integrate Stripe Listing Payment

This workflow covers fees paid to TheCountyPost for listings/upgrades. It does not cover buyer-to-seller payments or Stripe Connect.

## Read and inspect

- `docs/06-PAYMENTS-EXPIRATION.md`
- payment ADRs and approved price/refund policy
- listing lifecycle and transition services
- current Stripe configuration, orders, webhooks, tests, and reconciliation tools

## Implement in this order

1. Versioned internal price/product definition and eligibility checks
2. Local Order/OrderLine in a durable pending state
3. Server-side Checkout Session creation using calculated values
4. Safe success/cancel status pages that read local state
5. Raw-body signature verification and environment isolation
6. Unique StripeEvent persistence before processing
7. Idempotent, replayable event handlers
8. Transactional order/entitlement/listing transition handling
9. Reconciliation/replay management command and staff visibility
10. Refund/cancellation primitives only according to approved policy

## Non-negotiable invariants

- The browser never marks an order paid or activates/submits a listing.
- Only a verified webhook establishes durable payment truth.
- Duplicate, delayed, and out-of-order events are safe.
- Expected amount, currency, mode/account, order, and eligibility are revalidated.
- Event processing is observable without logging sensitive payloads.
- Test and live products/keys cannot cross.
- Payment success moves an eligible listing to `pending_moderation`, never directly to `active`.

## Test matrix

Include successful payment, abandoned checkout, wrong signature, duplicate event, out-of-order event, amount/currency mismatch, missing object, event retry after partial failure, replay command, refund path, featured entitlement dates, and concurrent processing.

Use Stripe CLI/test fixtures only for local verification; automated tests must not call Stripe.

## Output

Report money/state invariants, schema/migrations, webhook handlers, replay/reconciliation operations, tests, configuration, alarms, and remaining policy gaps.
