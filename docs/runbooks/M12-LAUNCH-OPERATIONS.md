# M12 Launch Operations Runbook

This is a rehearsal guide, not evidence of a completed launch, staging deploy, or
recovery exercise.

## Support

Verify the seller and listing IDs in staff tooling; do not request or record
payment-card data. Explain that a rejected paid listing receives a full refund
through the configured adapter, then route a missing or failed event to finance.
Do not expose provider references or internal moderation notes.

## Moderation

Use the staff moderation queue and an active reason code. Re-check the lifecycle
revision before recording an outcome. On rejection, confirm the seller-safe
notice and staff-only order/event audit after the transaction completes. Never
retry by changing order status directly.

## Finance

Use staff reconciliation and `replay_payment_events` for received/failed local
events. A full rejected-listing refund is keyed `local-refund-rejected-<order>`.
Duplicate processing is safe; mismatched currency/amount remains failed for
investigation. Production reconciliation requires the future Stripe adapter and
reviewed accounting process.

## Data repair, recovery, and rollback rehearsal

1. Capture a database backup and deployment image digest before any release.
2. Rehearse restoration to isolated staging; validate health, public visibility,
   moderation audit, orders, events, and outbox state.
3. For a failed release, roll back application image only when migrations are
   backward-compatible; otherwise use a forward fix. Do not delete audit,
   order, refund, or consent rows.
4. Replay durable outbox/payment events after recovery. Record expected and
   actual counts, timestamps, operator, and exceptions in the release record.

Required external rehearsal remains blocked until staging AWS resources and
access are provided.
