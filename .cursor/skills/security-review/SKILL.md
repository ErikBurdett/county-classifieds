---
name: security-review
description: Perform a threat-driven security and privacy review of a marketplace feature or diff and optionally fix confirmed issues.
argument-hint: "<feature spec, paths, or diff range>"
disable-model-invocation: true
---

# Security Review

Review first; do not make broad edits until findings are stated and scoped.

## Establish boundaries

Read the feature spec, `docs/07-SECURITY-PRIVACY.md`, relevant ADRs, code, templates, tests, settings, and infrastructure. Identify actors, assets, trust boundaries, data classification, and third parties.

## Threat review

Evaluate at minimum:

- authentication/session/account recovery
- object-level authorization and role escalation
- CSRF, XSS, injection, unsafe redirects, SSRF, and template safety
- mass assignment and client-trusted state
- enumeration and data leakage
- phone/email abuse and rate limiting
- upload authorization, file bombs, metadata, object-key attacks, and unsafe serving
- Stripe signature/idempotency/amount/state flaws
- moderation/admin abuse and audit gaps
- secrets/logging/analytics exposure
- race conditions, replay, scheduled-job duplication
- dependency and configuration risks
- AWS IAM, network exposure, encryption, backup, and presigned URL scope

## Findings format

For each finding provide:

- severity and confidence
- affected file/flow
- attack preconditions
- impact
- evidence
- concrete remediation
- regression test
- whether it blocks merge/release

Avoid speculative noise. Distinguish confirmed defects from defense-in-depth recommendations and unresolved policy.

## Fixing

When explicitly asked, fix only confirmed scoped findings, add negative tests, run the full gate, and document residual risk. Do not weaken security settings for local convenience.
