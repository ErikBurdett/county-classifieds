---
name: review-diff
description: Perform a senior engineering review of the current branch diff for correctness, scope, security, data safety, performance, and operability.
argument-hint: "[base ref or paths]"
disable-model-invocation: true
---

# Review Diff

Review only unless explicitly asked to fix selected findings.

## Establish scope

1. Inspect Git status, diff stat, full diff, commits, and untracked files.
2. Read the linked feature spec/ADR and relevant project docs.
3. Trace changed call paths; do not review isolated snippets only.

## Review checklist

- acceptance criteria and non-goals
- domain invariants and lifecycle transitions
- object authorization and role boundaries
- transaction, locking, retry, and idempotency behavior
- migration safety and compatibility
- query correctness, N+1 risks, indexes, pagination
- money, Stripe, reconciliation, and environment isolation
- upload/file handling and user-content rendering
- privacy, logs, metrics, notifications, and audit records
- error handling and useful failure states
- accessibility, responsive behavior, canonical URLs
- tests, false confidence, and missing negative cases
- dependency/config/IaC/secret changes
- documentation, runbook, rollout, and rollback
- unrelated or generated changes that should be removed

## Findings

Lead with findings ordered by severity. Each finding needs a precise file/line or flow, why it is wrong/risky, and a concrete correction. Do not bury blockers in a summary.

Then provide:

- assumptions/questions
- test/verification gaps
- concise change summary
- merge recommendation: block, changes requested, or ready

If there are no material findings, say so and list residual risks. Never claim code is safe because tests merely pass.
