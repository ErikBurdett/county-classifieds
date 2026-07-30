# Feature Specification: <ID — Title>

**Status:** Draft | Review | Accepted | Implementing | Released  
**Owner:** <name/role>  
**Milestone:** <M#>  
**Target release:** <release/date>  
**Last updated:** YYYY-MM-DD  
**Decision authority:** <stakeholder/role>

## 1. Outcome

### Problem

<What user or operational problem exists?>

### Desired outcome

<Observable result, not implementation language.>

### Success measures

- <measure and target>
- <quality/operational measure>

## 2. Traceability

### Source requirements

- <source section/quote or product-charter item>

### Accepted decisions

- ADR-XXXX: <title>

### Assumptions

- <assumption that is safe/reversible>

### Unresolved decisions/blockers

- <question, owner, needed-by date>

## 3. Scope

### In scope

- <behavior>

### Non-goals

- <explicitly excluded behavior>

### Deferred follow-ups

- <ticket/phase>

## 4. Actors and authorization

| Actor | May view | May create/change | Restrictions/audit |
|---|---|---|---|
| Anonymous buyer | | | |
| Seller | | | |
| Moderator | | | |
| Administrator | | | |
| System/worker | | | |

Define object ownership, staff permissions, suspension behavior, and forbidden actions.

## 5. User and operator flows

### Primary flow

1. ...

### Alternate/failure flows

- Validation failure:
- Unauthorized access:
- Third-party failure:
- Duplicate/retry:
- Stale/concurrent action:
- Empty state:

## 6. Behavior and business rules

Use MUST/SHOULD/MAY deliberately.

- <rule>
- <boundary condition>
- <calculation>
- <time/expiration behavior>

### State transitions

| Current state | Event/actor | New state | Preconditions | Side effects |
|---|---|---|---|---|
| | | | | |

## 7. Data design

### Models/fields

| Model | Field/change | Type | Null/default | Privacy | Reason |
|---|---|---|---|---|---|
| | | | | | |

### Invariants and constraints

- <DB constraint/service invariant>

### Query and index plan

- <main query path and index>

### Migration/backfill

- <expand/backfill/contract steps>

### Retention/deletion

- <approved behavior or unresolved decision>

## 8. Application design

### Domain services/transitions

- ...

### Selectors/read models

- ...

### Forms/validation/policies

- ...

### Views/URLs/templates/admin

- ...

### Background/outbox/schedules

- ...

### Third-party integration

- ...

## 9. URL, search, and SEO impact

- canonical path:
- redirects:
- query parameters:
- state/county scope:
- filters/sorts:
- indexability/robots:
- structured metadata/sitemap:

## 10. Security, privacy, and abuse cases

| Threat/abuse | Control | Test/evidence |
|---|---|---|
| Unauthorized object mutation | | |
| Enumeration/data leak | | |
| User-content injection | | |
| Replay/race/duplicate | | |
| Spam/automation | | |
| Sensitive log/notification | | |

## 11. Accessibility and responsive behavior

- keyboard/focus:
- labels/errors/status announcements:
- mobile/narrow layout:
- reduced motion:
- non-color cues:
- media/alt text:

## 12. Notifications and copy

| Trigger | Recipient | Channel | Template | Idempotency/suppression |
|---|---|---|---|---|
| | | | | |

List stakeholder-approved user-facing copy that affects policy.

## 13. Observability and operations

- structured log events:
- metrics:
- alarms:
- admin/reconciliation view:
- runbook updates:
- support escalation:

Do not include personal data or unbounded identifiers in metrics.

## 14. Test plan

| Layer | Scenario | Expected result |
|---|---|---|
| Unit | | |
| Model/constraint | | |
| Service/transaction | | |
| Selector/query | | |
| Request/template | | |
| Worker/schedule | | |
| Browser/manual | | |

Include permissions, invalid input, boundaries, duplicate/retry, concurrency, time, and third-party failure.

## 15. Rollout and rollback

### Deployment order

1. ...

### Feature flag/gradual release

<none or details>

### Data compatibility

<old/new task compatibility>

### Rollback/forward-fix

<steps and limitations>

### Post-deploy verification

- ...

## 16. Acceptance criteria

- [ ] Given ..., when ..., then ...
- [ ] Permissions and failure behavior are observable and tested.
- [ ] Migration/query/operational requirements are met.
- [ ] Documentation/runbooks are updated.

## 17. Implementation slices

| Slice | Outcome | Expected files/apps | Migration | Depends on |
|---|---|---|---|---|
| A | | | | |

## 18. Sign-off

| Role | Name | Decision | Date |
|---|---|---|---|
| Product | | | |
| Engineering | | | |
| Operations/moderation | | | |
| Security/legal, if required | | | |
