# Threat Model: <Feature/System>

**Owner:**  
**Date:**  
**Status:** Draft | Reviewed | Accepted  
**Feature spec/ADR:**

## Scope and assumptions

- In scope:
- Out of scope:
- Environment/dependencies:
- Assumptions requiring validation:

## Actors

| Actor | Trust level | Capabilities | Motivation/risks |
|---|---|---|---|
| | | | |

## Assets and data classification

| Asset/data | Classification | Location | Retention | Impact if exposed/changed/lost |
|---|---|---|---|---|
| | | | | |

## Trust boundaries and data flows

Describe or link a diagram. Include browser, Django web/worker, PostgreSQL, S3, Stripe, email/SMS, admin/moderators, and AWS control plane as relevant.

## Threats and controls

| ID | Threat/abuse case | Preconditions | Impact | Existing control | Gap/remediation | Test/evidence | Owner |
|---|---|---|---|---|---|---|---|
| T-01 | | | | | | | |

Consider:

- authentication/session/account recovery
- authorization/IDOR/role escalation
- input/output injection and XSS
- CSRF and unsafe redirects
- enumeration/data leakage
- rate-limit/spam/cost abuse
- upload/file/object-key attacks
- payment spoofing/replay/race/mismatch
- moderation/admin misuse
- background-job duplicate/retry behavior
- secrets/logs/analytics/notifications
- dependency/supply-chain/configuration
- AWS IAM/network/storage/database exposure
- availability and destructive actions

## Privacy review

- collection/minimization:
- public versus private fields:
- consent/notice:
- logging/analytics:
- retention/deletion:
- third parties:
- user access/correction:

## Residual risk and acceptance

| Risk | Severity | Reason not fully mitigated | Approver | Review date |
|---|---|---|---|---|
| | | | | |

## Verification and follow-up

- [ ] Negative tests added
- [ ] Configuration reviewed
- [ ] Logging redaction verified
- [ ] Runbook/alert updated
- [ ] Residual risks explicitly accepted
