# Application Architecture

## Style

Use a **modular monolith**: one Django deployment, one PostgreSQL database, one codebase, and explicit domain boundaries. The design should make future extraction possible without paying microservice complexity before it is justified.

## Module boundaries

### `core`

Shared base models, health endpoints, request IDs, common exceptions, clock abstraction, and utilities that have no domain owner. Avoid turning `core` into a dumping ground.

### `accounts`

Custom user model, authentication, seller profile, membership date, account status, staff roles, and phone-verification provider boundary. Account integration with existing news properties is provisional and must remain adapter-friendly.

### `locations`

State and county reference records, FIPS codes, slugs, lookup services, and route resolution. Listings reference normalized location rows rather than storing arbitrary state/county text.

### `catalog`

Vertical definitions, category hierarchy, allowed listing kinds, price products, durations, field-policy metadata, and feature flags. Catalog configuration must not become an EAV implementation for listing data.

### `listings`

The listing aggregate, typed vertical detail models, listing revisions if introduced, publication lifecycle, status history, and seller-management services.

### `media`

Upload authorization, S3 object keys, image records, order, processing state, dimensions, checksums, and moderation status. This module owns media lifecycle but not listing business transitions.

### `moderation`

Queue selection, moderator roles, review actions, reason codes, internal notes, suspension, escalation, and immutable audit events.

### `billing`

Orders, line items, Stripe Checkout sessions, webhook events, payment/refund state, featured upgrades, and reconciliation views. It does not process buyer-to-seller transactions.

### `favorites`

A small explicit relation between user and listing. It should remain isolated so saved searches and messaging do not become coupled to it.

### `notifications`

Email templates, delivery attempts, provider IDs, preferences, suppression awareness, and links to outbox work. Marketing consent and transactional notices must be distinct.

### `operations`

Transactional outbox, worker leasing, scheduled commands, backfills, data repair commands, and operational admin pages.

## Layers within an app

A typical app may contain:

```text
models.py              durable data and local invariants
services.py            transactional state changes
selectors.py           reusable query/read logic
forms.py               validation and user-facing form contracts
views.py               HTTP orchestration
urls.py                route definitions
admin.py               operational interface calling services
permissions.py         role/object authorization
policies.py            pure business rules
emails.py              notification composition
management/commands/   explicit operational jobs
```

Split files into packages only after a single file becomes difficult to navigate. Do not create abstraction directories without actual domain value.

## Transaction rule

Every workflow that changes business state must have one clearly named service entry point. The service:

1. Authorizes or requires an already-authorized actor.
2. Opens `transaction.atomic()`.
3. Locks mutable aggregate rows when concurrent updates are possible.
4. Validates the current state and requested transition.
5. Writes the aggregate change and immutable history/audit records.
6. Writes outbox events in the same transaction.
7. Returns a result object or updated aggregate.

External calls such as Stripe, SES, or S3 must not occur while holding a database transaction open unless the operation is explicitly designed for it.

## Read rule

Reusable listing browse/search queries belong in selectors or custom QuerySets. Views and admin classes should not independently recreate visibility rules. At minimum, public listing queries must centrally enforce:

- active status
- published time reached
- expiration not reached
- seller/account not suspended
- listing not administratively hidden
- category/location active
- media visibility rules

## Background work

Phase 1 uses a database-backed transactional outbox to avoid introducing Redis solely for jobs.

- Business transactions insert `OutboxEvent` rows.
- A separate worker command claims rows with `select_for_update(skip_locked=True)` and a lease timeout.
- Handlers are idempotent.
- Attempts, last error, next attempt, and completion are recorded.
- Poison events move to a failed state and alert operations.
- EventBridge starts scheduled commands for expiration, reminders, and digest preparation.

SQS may replace the polling transport later without changing domain event creation.

## Dependency direction

- Domain apps may depend on `core`, `accounts`, `locations`, and `catalog` as needed.
- `billing` may reference a listing/order but listing models must not import Stripe code.
- `notifications` consumes domain/outbox events; domain apps do not call SES directly.
- `moderation` calls listing services; listing status logic must not live only in admin actions.
- Future `messaging` must not become required to view or manage listings.

Circular imports are an architecture defect, not something to hide with local imports.

## API posture

Phase 1 does not require a public REST API. Use ordinary Django views and forms. Add JSON endpoints only for concrete needs such as direct-upload authorization or small progressive enhancements. If an external/mobile API is approved later, introduce it as a separate interface over the same services and selectors.

## Caching

Begin without distributed application caching. Use:

- proper indexes
- efficient `select_related`/`prefetch_related`
- per-request computed values
- HTTP caching for public static assets
- CloudFront for media

Introduce cache infrastructure only after measuring a bottleneck and documenting invalidation behavior.
