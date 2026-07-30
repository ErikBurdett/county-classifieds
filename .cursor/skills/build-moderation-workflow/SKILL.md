---
name: build-moderation-workflow
description: Implement or extend the moderation queue, decisions, audit trail, roles, and listing transition behavior.
argument-hint: "<accepted moderation feature spec>"
disable-model-invocation: true
---

# Build Moderation Workflow

## Read first

- `docs/03-LISTING-LIFECYCLE.md`
- `docs/05-MODERATION-OPERATIONS.md`
- `docs/07-SECURITY-PRIVACY.md`
- accepted moderation/prohibited-item decisions
- relevant listing, moderation, admin, and audit code

## Required design

- Explicit moderator roles and least-privilege permissions
- Queue selector with deterministic ordering and no public leakage
- Claim/assignment behavior if approved
- Approve, request changes, reject, suspend, and restore only where allowed
- Version/concurrency handling so stale moderator pages cannot overwrite newer decisions
- Reason codes distinct from private notes and user-visible explanations
- Immutable decision and status history
- Safe notification/outbox records after commit
- Listing/report/seller escalation links and audit visibility

## Guardrails

- Admin actions and views call the same domain transition services.
- Never assign status directly.
- A payment record does not bypass moderation.
- Moderators cannot see secrets or unnecessary payment/verification data.
- Private notes never render publicly or enter seller email unless explicitly copied into an approved public explanation field.
- Bulk actions require per-object authorization and transactional/error semantics.
- Do not invent prohibited-item policy or SLA.

## Tests

Cover permissions, transition matrix, stale decisions, duplicate submission, audit records, reason validation, notifications, public visibility before/after decisions, suspension, and staff query counts.

## Output

Describe the moderation operator flow, roles, state changes, records, notifications, tests, and runbook updates.
