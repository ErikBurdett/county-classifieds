---
name: debug-production-incident
description: Investigate a production-like marketplace incident safely, preserve evidence, mitigate impact, and produce a blameless incident record.
argument-hint: "<symptom, alert, or incident ID>"
disable-model-invocation: true
---

# Debug Production Incident

Safety and impact reduction come before code changes.

## Triage

1. State current time, environment, observed symptom, affected users/flows, and source of the alert.
2. Read `docs/11-OBSERVABILITY-RUNBOOK.md` and applicable service runbooks.
3. Establish an incident ID and timeline.
4. Check recent deployments, migrations, configuration changes, dependency incidents, and queue/database/payment health.
5. Use safe identifiers and redacted evidence. Do not paste secrets, full personal data, webhook payloads, or uploaded content into chat.

## Investigate

Form hypotheses and test them one at a time using logs, metrics, traces/query data, health endpoints, and reproducible read-only commands. Distinguish correlation from cause.

## Mitigate

Prefer reversible mitigations:

- rollback a known-bad image when schema-compatible
- disable a feature via an approved kill switch
- stop a scheduled task/worker causing harm
- increase capacity within known safe limits
- quarantine/replay durable work after the cause is fixed

Never delete audit/payment records or “fix” production data ad hoc without a reviewed, logged repair plan and backup.

## Resolve and learn

Verify recovery with user-visible and system metrics. Create an incident record covering timeline, impact, detection, root cause, contributing factors, mitigation, recovery, data integrity, follow-up owners/dates, and prevention tests/alarms/runbooks.

## Output

- impact/severity
- timeline and evidence
- leading/root cause status
- mitigation and verification
- data/payment/privacy implications
- follow-up actions
- whether stakeholder or legal/security notification is required by an approved policy
