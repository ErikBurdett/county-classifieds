# M9 Development Report

**Date:** 2026-07-23  
**Status:** Implementing

## Intended behavior

Listing notifications and expiration work are transactionally durable. The
outbox worker is a bounded, explicit management command; it claims PostgreSQL
rows safely, tracks attempts, retries failures, and supports operations replay.
Public listing reads remain independently fail-closed by expiration time.

## Changed areas

- `core.0001`: generic outbox events and delivery attempts with readiness,
  lease, aggregate, and idempotency indexes.
- `listings.0012`: append-only expiration action choice.
- Listing/billing lifecycle services create minimal notification events in
  their existing transactions. Demo publish paths remain event-free.
- Operations commands: `process_outbox`, `inspect_outbox`, `expire_listings`,
  and `schedule_listing_reminders`.
- Read-only outbox administration, local email templates, Make targets, and
  M9 feature/ADR/local-operation documentation.

## Security and operations

Payloads and structured logs use stable IDs and safe seller-facing text only;
they exclude private listing fields and email bodies. Production email requires
explicit SMTP/SES environment configuration. No AWS credentials, SES delivery
integration, or EventBridge infrastructure has been deployed.

## Verification

Verified 2026-07-23:

- `make check` passed: 154 tests passed, 5 PostgreSQL-only tests skipped, 4
  browser tests deselected, and total coverage was 85.65%.
- `make test-e2e` passed: 4 browser smoke tests passed.
- PostgreSQL-focused outbox tests passed: 9 tests passed.
- PostgreSQL `sqlmigrate` output for `core.0001` and `listings.0012` was
  reviewed; the local PostgreSQL migration apply completed successfully.
- Production deployment settings check completed with exit status 0 using
  deliberately non-secret validation values and reported no issues.
