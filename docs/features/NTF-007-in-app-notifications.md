# NTF-007 — In-app notifications

**Status:** Implemented locally (renewal/refund events remain deferred)  
**Authorization:** User-approved 2026-08-03

## Outcome

Authenticated users have an account-scoped notification inbox with an unread
badge in the site header. Notifications link only to destinations the recipient
is authorized to access, such as their listing or approved local payment action.

## Behavior

- Listing moderation, payment-link approval, payment completion, requested
  changes, rejection, expiration, renewal, and refund events create durable,
  idempotent in-app records in the same domain transaction as their business
  transition.
- The bell exposes an accessible unread count and feed. A user may mark one
  notification or all of their notifications read.
- Notification records store only seller-safe text. Internal moderator notes,
  private addresses, VINs, payment secrets, and provider payloads are never
  rendered in a notification.
- The outbox remains the asynchronous email delivery boundary. In-app records
  must not depend on an email worker succeeding.

## Security

Every feed query, read mutation, and destination resolution is scoped to the
authenticated recipient. Destination route names and parameters are server
allowlisted; arbitrary redirects are prohibited. Read mutations require POST
and CSRF protection.

## Rollout

The notification schema is additive with no historical backfill. Existing
outbox entries are not exposed as feed items. Read-notification retention is
not defined by this local slice and no purge job is introduced.
