---
name: release-readiness
description: Run a comprehensive milestone or production release gate and produce a go/no-go assessment with evidence.
argument-hint: "<release, milestone, or environment>"
disable-model-invocation: true
---

# Release Readiness

Read `docs/15-DEFINITION-OF-DONE.md`, `docs/19-LAUNCH-CHECKLIST.md`, the release feature specs/ADRs, and current runbooks.

## Verify evidence

Assess:

- approved scope and acceptance criteria
- unresolved P0/P1 decisions
- Git/CI status and release artifact provenance
- migrations, locks, deploy compatibility, and rollback/forward-fix
- automated test matrix and manual journey results
- authorization/security/privacy/threat review findings
- payment/webhook reconciliation and live/test isolation
- media upload/processing/access controls
- moderation staffing, policies, queue, and escalation
- email deliverability, templates, consent, suppression, and failure behavior
- expiration/renewal/scheduled jobs and duplicate safety
- performance/load/query results and capacity limits
- accessibility and responsive/brand review
- production configuration, DNS/TLS, health, autoscaling, alarms, logs, dashboards
- backups, point-in-time recovery, and restore rehearsal
- support, incident, refund, abuse, and rollback ownership
- analytics/SEO/canonical/robots/sitemap behavior
- seed inventory and launch content quality

## Run checks

Run every locally/CI-accessible check and record actual results. For checks requiring AWS/Stripe/stakeholder access, mark evidence as supplied, missing, or failed—never assume.

## Output

Create a release review from `templates/RELEASE-CHECKLIST.md` with:

- release identifier/date/commit/image digest
- passed/failed/missing evidence
- blockers and owners
- accepted risks with approver
- deployment and verification sequence
- rollback triggers
- final recommendation: GO, CONDITIONAL GO, or NO-GO

A release with unverified payment integrity, migration safety, backup recovery, critical authorization, or production secrets/configuration is NO-GO.
