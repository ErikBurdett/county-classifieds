---
name: implement-django-feature
description: Implement one accepted Django marketplace feature specification with tests, documentation, and disciplined scope.
argument-hint: "<accepted feature spec path>"
disable-model-invocation: true
---

# Implement Django Feature

Implement exactly one accepted feature specification or one explicitly named slice from it.

## Before editing

1. Read the entire accepted feature spec and referenced ADRs/docs.
2. Inspect the implementation paths and current tests.
3. Confirm Git status and avoid overwriting unrelated work.
4. State:
   - behavior being implemented
   - explicit non-goals
   - files expected to change
   - migration impact
   - authorization/security impact
   - test plan
5. Stop and report any contradiction or missing decision that materially changes behavior.

## Implementation order

Prefer this sequence where applicable:

1. invariants, constraints, value objects, and models
2. safe migration(s)
3. domain transition/service logic
4. selectors/read models
5. forms/input validation and policies
6. views/URLs/admin adapters
7. templates/progressive enhancement
8. background/outbox/notification adapters
9. tests at appropriate layers
10. docs/runbooks/feature status

## Standards

- Keep domain workflows explicit and transactionally safe.
- Use centralized authorization, transition, pricing, and public-visibility boundaries.
- Avoid signals for primary behavior.
- Keep templates presentation-only.
- Do not add dependencies unless justified and locked.
- Preserve backward compatibility during deploy when schema and code cannot change atomically.
- Do not broaden scope to “helpful” adjacent features.

## Verify

Run narrow tests throughout, then the full repository gate. Inspect generated migration SQL and query behavior. Exercise the user-visible flow locally when feasible.

## Deliver

Report:

- behavior completed versus deferred
- files and migration(s)
- security/permission decisions
- tests/commands actually run and outcomes
- manual verification performed
- deployment/rollback notes
- remaining risks or follow-up tickets

Do not claim completion if acceptance criteria are not demonstrated.
