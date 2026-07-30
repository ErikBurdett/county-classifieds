# Payments, Featured Placement, Renewal, and Expiration

## Scope boundary

Stripe collects fees paid to TheCountyPost for listing publication and upgrades. The application does not collect buyer purchase money, hold escrow, pay sellers, or use Stripe Connect in MVP.

## Product catalog

Application-owned product records define:

- eligibility by vertical/listing kind
- amount and currency
- publication duration
- whether moderation is required
- renewal behavior
- effective date range

Stripe Product/Price IDs are environment-specific mappings. The server determines the price; clients never submit trusted amounts or Stripe Price IDs.

Source pricing is a starting business proposal, not code constants:

- community posting: free with short expiration
- standard marketplace listing: paid with a shorter term
- selected higher-value verticals: higher fee with a longer term
- featured placement: additional fee
- dealer plans: deferred

## Order flow

1. Seller completes a valid draft.
2. Server selects eligible products and creates an immutable order/line snapshot.
3. Server creates a Stripe Checkout Session with an idempotency key and metadata containing only stable internal IDs.
4. Browser is redirected to Stripe-hosted Checkout.
5. Success/cancel routes show current application order state; neither route marks an order paid.
6. Verified Stripe webhook is stored by unique event ID.
7. Idempotent handler retrieves/validates relevant Stripe objects when needed.
8. Handler marks the order paid and transitions the listing to moderation in one transaction.
9. Notification/outbox events are created.

## Webhook requirements

- Use the raw request body for signature verification.
- Reject invalid signatures without processing.
- Persist each Stripe event ID uniquely before/while processing.
- Treat delivery order as arbitrary.
- Process events idempotently and safely on retry.
- Do not log full payloads containing unnecessary personal information.
- Distinguish test and live mode.
- Alert on sustained failures or event age.
- Provide a staff reconciliation view and a replay command that calls the same handler.

Likely events include Checkout completion, async payment success/failure, charge refunds, and disputes. Implement only events required by the selected Stripe flow and document each handler.

## Payment state versus listing state

Order and listing states are separate. Examples:

- an order may be paid while a listing is pending moderation
- a listing may be rejected while an order awaits refund policy action
- a listing may be active while a separate featured-upgrade order fails
- a dispute may suspend an entitlement without erasing the historical payment

Never infer payment truth from listing status.

## Featured upgrades

A successful featured line creates a time-bounded `FeaturedPlacement`. Define:

- placement surface
- start behavior if listing is still pending moderation
- end date
- whether time lost during suspension is restored
- refund treatment
- inventory limit/rotation

Provisional default: placement begins when the listing becomes active, not at Checkout completion.

## Rejected paid listings

This is a P0 business decision. The implementation must support:

- no refund
- automatic full refund
- manual refund review
- correction window before refund
- partial refund if a non-refundable upgrade/service is defined

Do not automate refunds until the approved policy and user-facing terms agree. Refund attempts and results must be idempotent and auditable.

## Renewal

- Create a new order; never mutate the original order.
- Calculate entitlement from server-side product configuration.
- Do not extend a listing on return-page load.
- Decide whether unchanged listings bypass re-moderation within a grace period.
- Prevent two concurrent renewal payments from granting duplicate time.
- Send renewal confirmation from an outbox event after durable state change.

## Expiration processing

A scheduled idempotent command:

1. selects eligible active listings in bounded batches
2. locks rows
3. transitions to expired
4. closes active featured placements as policy requires
5. records status history
6. emits notification and search-removal events

The public selector must independently exclude expired timestamps so a delayed scheduler does not leave stale listings visible.

## Reminders

Email reminders should be generated from durable scheduled work, not a long-running web request. Track delivery to prevent duplicates. Exact reminder timing, frequency, and content are product decisions.

## Disputes and chargebacks

Define an administrative playbook before launch:

- identify order/listing/seller
- suspend paid entitlement if policy requires
- preserve moderation and payment evidence
- record response owner/deadline
- avoid exposing sensitive dispute details to unauthorized staff

## Reconciliation

Staff must be able to trace:

```text
Listing → Order → Order lines → Checkout Session/Payment → Stripe events → Refund/dispute
```

Nightly or scheduled reconciliation should detect paid Stripe sessions not reflected locally and local paid orders with missing provider confirmation.
