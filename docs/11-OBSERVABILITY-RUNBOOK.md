# Observability and Operational Runbook

## Principles

- Every production failure should be traceable from a user-visible request or background event to structured logs and durable business records.
- Logs are not the source of truth for payments, moderation, listing state, or notification delivery.
- Alerts should indicate user or business impact and identify an owner/action.
- Operational commands are idempotent, bounded, documented, and dry-run capable where practical.

## Structured logging

Include:

- timestamp and level
- environment/service/version
- request or correlation ID
- route/view and response status
- actor/user ID where allowed, never unnecessary PII
- listing/order/outbox/provider event IDs
- event type and outcome
- exception class and safe message
- latency

Use consistent event names such as:

```text
listing.submitted
listing.moderation.approved
order.checkout.created
stripe.event.processed
outbox.event.failed
media.processing.failed
scheduled.expiration.completed
```

## Metrics

### HTTP

- request count/status
- latency percentiles
- 4xx/5xx by route class
- load balancer unhealthy targets
- task restarts and saturation

### Database

- connections and connection wait
- CPU/storage/IO
- slow queries
- lock waits/deadlocks
- replica/backup state if applicable

### Business workflows

- drafts/submissions/active listings
- order and Checkout completion
- moderation queue depth/age
- expiration backlog
- outbox pending age and failures
- webhook receipt-to-processing age
- media processing failures
- notification failures/bounces/complaints

## Alerts

Each alert documents:

- threshold/condition
- severity
- owner
- initial diagnosis links/queries
- mitigation
- escalation
- false-positive notes

Minimum launch alerts:

- sustained 5xx/error-rate increase
- no healthy web targets
- database storage or connection pressure
- production task crash loop
- Stripe webhook failures or oldest unprocessed event age
- outbox oldest pending age
- failed expiration/scheduled job
- media processing failure spike
- SES bounce/complaint anomaly
- backup/PITR failure
- certificate/domain issue

## Standard incident sequence

1. Confirm impact and environment.
2. Assign incident lead and communication channel.
3. Stop harmful change or traffic path if needed.
4. Preserve identifiers and evidence; avoid ad hoc database edits.
5. Use documented rollback, feature flag, or suspension path.
6. Reconcile durable business state after service recovery.
7. Communicate user impact using approved channels.
8. Record timeline, root cause, contributing factors, and follow-up work.

## Runbook: failed deployment

- check ECS deployment/task events and health endpoint
- compare image digest and configuration with prior release
- inspect startup logs and secret/config injection
- confirm migration status
- if schema remains backward compatible, roll service to prior image digest
- if migration is involved, follow the release-specific rollback plan; never reverse blindly
- run smoke tests and monitor before closing

## Runbook: webhook backlog

- verify endpoint reachability and signature configuration
- inspect oldest failed/unprocessed `StripeEvent`
- confirm no broad provider outage
- pause manual replay if handler defect could duplicate effects
- deploy fix with idempotency tests
- replay bounded events through the same handler
- reconcile orders/listings and alert age

## Runbook: outbox backlog

- inspect worker health, leases, error distribution, and oldest age
- distinguish poison event from capacity issue
- fix handler or dependency
- release expired leases safely
- replay bounded event types
- confirm duplicate-safe behavior and downstream state

## Runbook: moderation queue growth

- verify submission spike versus staff availability/system defect
- check queue selectors and claim leases
- prioritize oldest/high-risk according to policy
- communicate SLA impact
- do not bypass moderation to reduce the number

## Runbook: S3/media issue

- disable new upload finalization with a feature flag if harmful
- preserve existing public images and listing browsing where possible
- inspect bucket policy, KMS, presign expiry, processor, and CloudFront
- retry idempotently by image state
- never make the bucket public as a quick fix

## Data repair

Production data fixes require:

- issue/incident reference
- dry-run output
- bounded selector
- idempotent command or reviewed SQL
- backup/restore awareness
- before/after counts
- audit record
- peer review

Avoid editing business rows manually in Django shell without a saved, reviewed procedure.
