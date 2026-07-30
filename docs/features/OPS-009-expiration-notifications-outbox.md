# OPS-009: Expiration, notifications, and durable outbox

## Problem and scope

Listing lifecycle changes must remain durable when a request or worker fails.
This slice adds PostgreSQL-backed outbox records, owner notification events,
7/3/1-day expiration reminders, and explicit operational commands. It does not
deploy SES, EventBridge, or any asynchronous queue.

## Actors and behavior

- Moderators create approved, changes-requested, and rejected notifications in
  the same transaction as the listing transition.
- Owners marking listings sold create a sold notification transactionally.
- The scheduled expiration command locks due published listings, expires them,
  records an audit action, and creates an expiry notification.
- The reminder scheduler creates at most one delayed event for each listing,
  expiration timestamp, and selected 7/3/1-day offset.
- An operator explicitly runs the outbox worker. It leases rows using
  `select_for_update(skip_locked=True)`, records attempts, and retries bounded
  failures with exponential delay.

## Data, security, and observability

`OutboxEvent` stores a type, JSON payload, aggregate reference, availability,
lease, processing/failure timestamps, attempts, and a unique idempotency key.
`OutboxDeliveryAttempt` is append-only. Email payloads contain only a listing
UUID, selected reminder offset, and staff-approved seller-facing text; they do
not include phone numbers, VINs, internal moderation notes, or payment data.

`inspect_outbox` reports pending count, failed count, and oldest pending age.
Worker logs contain event identifiers/type and counts, never payloads or email
bodies. The Django admin offers read-only filtered operations lists.

## Migration and rollout

`core.0001` creates additive outbox tables and indexes. `listings.0012` adds
the append-only expiration audit action choice. Apply migrations before
enabling scheduled invocations. Rollback stops commands/workers; existing
events and audit records remain for a forward fix.

## Acceptance criteria

- Domain state and outbox event insertions roll back together.
- Leased events are not concurrently processed and expired leases are recoverable.
- Delivery retries are bounded and terminal failures can be explicitly replayed.
- The public selector still hides rows by `expires_at` before expiration runs.
- Demo seed publication emits no notification event.
