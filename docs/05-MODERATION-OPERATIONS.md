# Moderation and Marketplace Operations

## Purpose

Moderation is not a single approve/reject button. It is a controlled operational workflow that protects brand quality, prevents prohibited inventory, gives sellers actionable feedback, and leaves a defensible audit trail.

## Roles

Create Django groups and explicit permissions rather than checking `is_staff` alone.

### Marketplace Administrator

- manage staff roles and policy configuration
- suspend/restore accounts
- override listing state through audited services
- manage categories, products, reason codes, and feature flags
- access all moderation and finance-support views

### Senior Moderator

- all moderator actions
- resolve escalations
- suspend/restore listings
- recommend or perform account suspension according to policy
- review disputed actions

### Moderator

- view assigned/unassigned queue
- approve
- request changes
- reject using allowed reason codes
- add internal notes
- escalate

### Support

- view seller/listing/order history needed for support
- resend permitted notifications
- create support notes
- no approval, refund, or suspension authority by default

### Finance/Read-only Operations

- view orders, Stripe references, refunds, and reconciliation data
- no listing-content edits
- refund authority is a separate permission

## Queue behavior

The moderation queue should support:

- oldest submitted first by default
- filters by vertical, county/state, risk flag, submission age, and prior change request
- claim/assignment with visible ownership and lease timeout
- preview of public rendering
- seller/profile history
- payment/product context without exposing unnecessary payment details
- image review at useful resolution
- duplicate candidates and automated flags when available
- keyboard-efficient but confirmation-safe actions

A moderator opening a row does not permanently lock it. State-changing actions use database locking and detect stale reviews.

## Review outcomes

### Approve

- validate listing is still in `pending_moderation`
- record moderator and action
- set publication/expiration entitlement
- emit notification and indexing events

### Request changes

- one or more controlled reason codes
- seller-visible explanation with specific corrective action
- optional internal note
- transition to `changes_requested`
- no public visibility

### Reject

- controlled reason code
- seller-visible explanation according to policy
- refund/escalation task when applicable
- transition to `rejected`

### Suspend

Used after publication for policy, fraud, safety, payment, or account issues. Suspension must record severity, public behavior, seller notice, and escalation status.

### Escalate

Creates an assigned case for a senior moderator/administrator. The listing remains in the safest policy-defined state while pending.

## Reason taxonomy

Reason codes should distinguish at least:

- incomplete or inaccurate structured fields
- insufficient/poor-quality/duplicate images
- misleading title/description
- wrong category
- duplicate listing
- prohibited item/service
- suspected scam or impersonation
- unsafe/contact-policy issue
- price/location inconsistency
- VIN/serial/privacy issue
- policy/legal escalation
- payment/product mismatch

Reason codes have:

- internal label
- seller-visible title and guidance
- action types for which they are valid
- severity
- whether escalation is mandatory
- whether refund review is required
- active/versioned status

Do not delete reason codes used by history.

## Editing versus rejecting

Moderators should not silently rewrite seller claims, prices, item condition, or material facts. They may correct strictly non-substantive formatting only if policy allows and the action is audited. Otherwise request changes.

## Duplicate handling

A duplicate policy must define:

- same seller and same item thresholds
- cross-posting across categories/counties
- renewal versus duplicate
- dealer inventory exceptions later
- which record remains active
- whether fees transfer or refund

Automated similarity is advisory; a moderator makes the final decision in MVP.

## Scam escalation

Suspected scam actions may include:

- immediate listing suspension
- account login/session review
- phone re-verification
- related listing lookup
- preserving evidence and request IDs
- support/administrative escalation
- user communication using approved templates

Staff must not promise law-enforcement action or expose detection details without policy approval.

## Post-publication reports

RPT-001 provides anonymous or authenticated in-product reporting only for
currently public listings. The report form is CSRF-protected and always returns
the same receipt for accepted, nonpublic, duplicate, and rate-suppressed POSTs.
It stores a HMACed source-address identifier, never a raw IP address.

Staff holding `reports.triage_listingreport` triage reports at
`/staff/reports/`. Each queued report has a separate CSRF-protected form and
may be acknowledged, resolved, dismissed, or escalated through a locked,
append-only report-action service. Feedback is generic and actionable; report
data is not repeated in errors. Closed reports cannot be changed.

Reviewers may follow a report to its public listing only while that listing is
still public. Holding `listings.moderate_listing` additionally exposes the
existing moderation queue, but report triage never changes a listing
automatically. Explicit reporter email is shown first; otherwise the
authenticated reporter email is restricted to authorized report reviewers.
Sellers and the public do not see report, reporter, internal-note, assignment,
or audit data.

There are no reporter notifications, evidence attachments, reporter report
history, or automatic enforcement. Report retention, deletion exceptions,
access review, and escalation evidence procedures remain pending legal/product
approval in `RPT-001-REPORT-RETENTION-PROPOSAL.md`.

## Audit requirements

Every staff state-changing action records:

- actor
- role/permission path
- target
- prior and resulting state
- controlled reason
- seller-visible and internal notes separately
- timestamp
- request/correlation ID
- optional related order/report/case

Audit records are append-only in ordinary application use. Staff actions must call services rather than editing status fields directly in Django Admin.

## Operational metrics

- queue depth by age/vertical
- median and percentile review age
- approval/change/rejection rates
- re-review rate
- moderator throughput with quality safeguards
- escalations and unresolved age
- post-publication report rate
- restored/successfully appealed actions
- suspected-scam and duplicate rate

Metrics are for system health and training, not simplistic individual quotas.
