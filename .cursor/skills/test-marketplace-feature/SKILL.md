---
name: test-marketplace-feature
description: Build and execute a risk-based test plan for a marketplace feature, filling meaningful coverage gaps.
argument-hint: "<feature spec, ticket, or changed paths>"
disable-model-invocation: true
---

# Test Marketplace Feature

## Discover

Read the accepted spec and acceptance criteria. Trace changed behavior and existing tests. Do not equate line coverage with behavioral confidence.

## Build a risk matrix

Include relevant combinations of:

- actor/role/ownership
- listing/payment/moderation state
- state/county scope and vertical
- valid/invalid/boundary input
- duplicate/retry/concurrent execution
- time before/at/after expiry
- third-party success/failure/timeout
- privacy/public-versus-staff output
- mobile/keyboard/accessibility behavior

## Add tests at the lowest useful layer

- unit tests for pure policies/value objects
- model/constraint tests for invariants
- service tests for transactions and transitions
- selector tests for visibility/filtering/query shape
- request tests for permissions/forms/redirects
- template tests for safe output and states
- browser tests for only the critical integrated journeys
- management-command/worker tests for retries and schedules

## Execute

Run the narrowest tests first, then formatting/lint/type/Django/migration checks and the full suite. Use deterministic clocks and fakes; never call production-like external services.

## Output

- acceptance-criterion coverage map
- tests added/changed
- commands and exact results
- gaps intentionally deferred with reason
- flaky/slow/query issues found
- merge recommendation

Do not modify product behavior solely to make an incorrect test pass; reconcile tests with the accepted spec.
