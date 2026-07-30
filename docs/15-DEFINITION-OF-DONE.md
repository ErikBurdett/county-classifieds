# Definition of Done

A feature is done only when all applicable items are true.

## Product and scope

- Accepted feature specification exists.
- Behavior matches an approved decision; no silent scope additions.
- Out-of-scope behavior and follow-up work are recorded.
- User-facing copy and failure states are reviewed.

## Architecture and data

- Correct domain module owns the behavior.
- State changes use a named transactional service.
- Read logic uses shared selectors/querysets where visibility matters.
- Database constraints and indexes are intentional.
- Migration is reviewed, reversible/compatible as documented, and safe for expected data volume.
- No EAV or unbounded JSON is introduced for filterable business data.
- Audit/history/outbox requirements are implemented.

## Security and privacy

- Object permissions and negative cases are tested.
- Input length/type/rate limits are considered.
- Secrets and PII do not leak to templates, logs, events, or analytics.
- Upload/payment/auth changes complete a threat review.
- Staff privileges remain least-privilege.
- User content remains escaped/sanitized according to policy.

## Testing and quality

- Unit/service/view/integration tests cover normal and failure behavior.
- Idempotency and concurrency are tested where relevant.
- Regression test exists for fixed bugs.
- Ruff, mypy, pytest, coverage, migration check, and Django checks pass.
- Representative query count/performance is reviewed for browse/admin/list pages.
- Browser test is added or updated for critical journeys.

## UI and accessibility

- Uses approved components and semantic tokens.
- Responsive behavior is verified.
- Keyboard, labels, focus, errors, contrast, and non-color status communication are checked.
- Loading, empty, error, and success states exist.
- No unverified brand literals are scattered in templates/styles.

## Operations

- Structured logs/events/metrics exist where the workflow can fail operationally.
- Background handlers are retry-safe and observable.
- Admin/support workflow is usable without database access.
- Runbook or operational documentation is updated.
- Feature flag has owner/default/removal plan if used.
- Rollout and rollback/data compatibility are documented.

## Documentation and review

- ADRs and data model docs reflect the implementation.
- Roadmap/backlog status is updated.
- PR explains risk, migrations, tests, screenshots, and manual verification.
- Diff receives independent review.
- No unresolved high-severity review finding remains.
