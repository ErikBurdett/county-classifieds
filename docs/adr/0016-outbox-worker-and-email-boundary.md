# ADR 0016: Explicit PostgreSQL outbox worker and email boundary

- Status: Accepted
- Date: 2026-07-23

## Context

ADR 0006 selected a transactional outbox but left worker and email delivery
details to M9. This milestone must be demonstrable locally without AWS
credentials or an async queue.

## Decision

Use a generic `core.OutboxEvent` with a unique idempotency key and
aggregate-reference fields. Workers lease records with PostgreSQL row locks and
`skip_locked`, write a delivery attempt for each claim, and retry bounded
failures after exponential delays. Listing notification handlers use Django's
configured email backend and minimal event payloads.

M9 supplies management commands only. An operator or future scheduler invokes
`expire_listings`, `schedule_listing_reminders`, and `process_outbox`
explicitly. SES configuration remains a production settings boundary that
fails closed; no EventBridge or SES infrastructure is introduced here.

## Consequences

- Side effects are durable and observable without Redis, Celery, or SQS.
- A mail backend without provider-side idempotency can still have at-least-once
  delivery after a process crash during provider I/O; application state and
  normal replays remain idempotent.
- Production scheduling, SES domain verification, bounce handling, and alarms
  remain M11 deployment work.
