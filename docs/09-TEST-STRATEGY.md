# Test Strategy

## Goals

Tests protect business transitions, permissions, money, moderation, search visibility, and deployment safety. They are not a pursuit of line coverage without behavior confidence.

## Test layers

### Unit tests

Use for pure policies, validators, pricing calculations, route normalization, filter parsing, and state-transition rules.

### Model/constraint tests

Verify database-level uniqueness, check constraints, protected deletion, compatible state/county relations, and one-detail-model rules where implemented.

### Service integration tests

The most important layer. Exercise the real database and assert:

- authorized state transitions
- history/audit rows
- outbox events
- locking/concurrency behavior where relevant
- idempotency
- rollback on failure

### View/form tests

Verify status codes, redirects, rendered errors, CSRF-sensitive behavior, object authorization, form contracts, and public visibility.

### Provider-boundary tests

Mock at the HTTP/provider boundary, not deep inside business logic.

- Stripe signature/event fixtures and replay
- S3 upload authorization/finalization
- phone verification adapter
- SES/notification adapter

Keep sanitized provider fixtures versioned and small.

### End-to-end tests

Use browser tests for a compact set of critical journeys:

- signup/verification boundary
- create free listing and submit
- paid listing Checkout handoff with test-mode/webhook simulation
- moderator review
- buyer browse/detail/favorite
- seller marks sold/renews

E2E tests do not replace service tests.

## Required behavior matrices

### Listing transition matrix

Every allowed transition has a success test. Every disallowed transition has a failure test. Include seller, moderator, administrator, suspended account, stale state, and repeated request cases.

### Payment matrix

- valid completion
- duplicate event
- event out of order
- async success/failure
- invalid signature
- unknown order/session
- amount/currency/product mismatch
- refund replay
- featured upgrade before/after listing activation

### Visibility matrix

Test active, pending, expired, suspended, sold, archived, future-published, expired timestamp with stale status, inactive category, and suspended seller across browse, detail, sitemap, and favorites.

### Upload matrix

Test content type, extension mismatch, oversized bytes, excessive dimensions, corrupt image, too many images, unauthorized listing, expired upload session, reused key, metadata stripping, and processing failure.

## Factories and fixtures

- Use Factory Boy or focused factory functions.
- Default factories create valid minimal objects.
- State-specific factories make transitions explicit.
- Seed/reference fixtures are versioned and validated separately.
- Avoid massive opaque global fixtures.
- Freeze time with `time-machine` for expiration and entitlement tests.

## Coverage policy

- Critical domain services, webhook handlers, permission policies, and transition logic require comprehensive branch coverage.
- Establish an initial project coverage floor during bootstrap and never lower it to merge a feature.
- Exclude generated migrations and boilerplate only by documented configuration.
- Mutation testing may be introduced for high-risk pricing/transition modules after the baseline suite is stable.

## Performance tests

Before launch, seed realistic data and measure:

- statewide and county category browse
- common vertical filters
- text search
- moderation queue
- seller dashboard
- expiration batches
- outbox throughput

Record query count and representative execution plans. Prevent N+1 regressions with targeted assertions.

## CI quality gate

At minimum:

```text
ruff format --check
ruff check
mypy
pytest with coverage
makemigrations --check --dry-run
django system checks
collectstatic
production check --deploy
package vulnerability audit
```

A failed test is fixed or the behavior decision is changed and documented. Do not weaken assertions simply to restore green CI.
