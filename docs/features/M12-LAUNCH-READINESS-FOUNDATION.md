# M12 — Launch Readiness Foundation

**Status:** Implementing  
**Milestone:** M12  
**Last updated:** 2026-07-23

## Scope

This foundation supplies durable local billing-refund behavior, versioned policy
records, draft-document seeds, and local operational evidence. It is not a
production launch or legal approval.

## Behavior and safety

- A moderator rejection of a paid local-demo listing creates one full refund
  event, keyed to the immutable order. Duplicate or delayed processing cannot
  refund the same order twice. Browser routes cannot initiate refunds.
- Payment events and order state remain staff-only; public listing surfaces do
  not expose provider references, amounts, or refund history.
- Policy documents are versioned and may be `draft`, `active`, or `retired`.
  Draft seeds say they are non-binding, project-owner review material. Active
  listing-required documents must be accepted for each listing submission.
- Activation requires a supplied named legal entity; the seed never supplies
  one and does not claim counsel review.

## Operations and rollout

Use only in DEBUG/operator-safe local environments:

```bash
make seed-draft-policy-documents
make launch-smoke
```

`make launch-smoke` runs `uv run python src/manage.py launch_smoke` with the
default local settings; it does not take a `--local` option.

Runbook and rehearsal instructions are in `docs/runbooks/`. Production rollout
requires a reviewed Stripe adapter, external environment configuration, and a
separate staging/recovery rehearsal.

## Acceptance and remaining blockers

Tests cover refund event audit/idempotency, moderator authorization, policy
draft/activation validation, and local workflow checks. Remaining launch
blockers: named legal entity and counsel review; Stripe, SES, AWS, DNS, ACM and
monitoring production configuration; staging deployment and restore rehearsal;
and staff training.
