# ADR 0006: Use a PostgreSQL Transactional Outbox for Phase 1

- Status: Accepted
- Date: 2026-07-22

## Context

Listing transitions trigger email, media, expiration, and integration work. Calling external services inside web transactions is unreliable. Introducing Redis only for a job queue increases infrastructure and deployment complexity.

## Decision

Record `OutboxEvent` rows in the same PostgreSQL transaction as business state. Process them with a separate Django worker using row leases and `select_for_update(skip_locked=True)`. Use EventBridge for scheduled command invocation. Keep handlers idempotent so transport may later move to SQS.

## Consequences

- Atomic business state plus event creation.
- Database polling/load must be bounded and monitored.
- Worker leasing, retries, poison events, and replay tooling must be implemented carefully.
- SQS/managed queue remains a future transport option without changing domain services.
