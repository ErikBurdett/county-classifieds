---
name: plan-marketplace-feature
description: Turn a marketplace milestone, issue, or request into a reviewable implementation-ready feature specification without writing production code.
argument-hint: "<ticket, milestone slice, or feature description>"
disable-model-invocation: true
---

# Plan Marketplace Feature

Planning only. Do not edit production code or create migrations.

## Discover

1. Read the cited request plus the relevant roadmap, backlog, product charter, architecture, domain model, lifecycle, security, testing, and accepted ADRs.
2. Inspect existing models, services, selectors, forms, URLs, templates, admin, tests, and migrations that the feature would touch.
3. Trace current behavior end-to-end. Do not plan from filenames alone.
4. Identify unresolved product decisions, hidden scope, data migration needs, third-party dependencies, abuse cases, and operational ownership.

## Design

Create `docs/features/<ticket>-<slug>.md` from `templates/FEATURE-SPEC.md` with:

- problem and outcome
- source/decision traceability
- actors and permissions
- in-scope behavior and explicit non-goals
- user flows and failure states
- domain invariants and allowed state transitions
- data/schema/index impact
- services/selectors/forms/views/templates/admin boundaries
- URL/canonical/search impact
- security, privacy, abuse, and accessibility cases
- emails/background work/observability
- migration/backfill/rollout/rollback plan
- test matrix
- acceptance criteria written as observable behavior
- implementation slices small enough for separate commits/PRs

## Challenge the plan

Check for:

- direct status assignment instead of transition services
- duplicated public visibility logic
- browser-trusted price or payment state
- authorization enforced only in templates
- user content crossing an unsafe rendering boundary
- unbounded queries, N+1 behavior, or missing indexes
- policy being invented in code
- Phase 1B/later scope accidentally pulled into MVP

## Output

Return:

1. spec path
2. concise design summary
3. decisions/blockers
4. proposed implementation slices in order
5. migration and operational risk
6. exact first slice recommended

Stop after planning and wait for review of the committed spec.
