# RPT-001: Public Listing Reports

**Status:** implemented locally  
**Decision:** DEC-109 accepted 2026-07-23

## Problem and scope

Visitors need a safe, monitored way to report a currently public listing without
revealing the report to its seller. This slice provides anonymous or
authenticated in-product reports for public listings, a staff-only triage
queue, immutable action history, and no automatic listing enforcement.

It excludes email/phone verification, reporter updates, evidence uploads,
Community Board posting, user blocking, and automated listing actions.

## Actors and permissions

- Anonymous and authenticated visitors may submit the public form.
- Only staff with `reports.triage_listingreport` can access the queue or record
  acknowledge, resolve, dismiss, or escalate actions.
- The `moderator` staff group receives the narrow report view and triage
  permissions through `provision_staff_groups`.
- Sellers and public visitors never receive report, reporter, internal note,
  assignment, or audit-history data.

## Behavior and data

`ListingReport` records the public listing, optional authenticated reporter,
optional private email, fixed reason, bounded description, HMACed source
address, duplicate fingerprint, state, assignment, and timestamps.
`ListingReportAction` is append-only and captures submission and each staff
transition with optional internal note.

Accepted reasons are scam/fraud, prohibited item or service, suspected stolen
or counterfeit item, inaccurate or misleading content, and abuse/other.
Public POST responses use the same generic receipt for success, a missing or
nonpublic listing, rate limiting, and duplicate suppression. GET only displays
the form for a current public listing. Browser POSTs remain CSRF-protected.

The staff queue renders one independently prefixed, CSRF-protected triage form
per routed report ID, so label and control IDs remain unique across queue rows.
It uses POST/redirect/GET feedback for recorded, invalid, closed/stale, missing,
and unauthorized actions without exposing report details in feedback. Reviewers
can open the public listing only while it remains public. A reviewer who also
holds `listings.moderate_listing` can open the existing moderation queue; this
does not create a report-driven listing action or a private listing route.

The queue displays an explicit private reporter email first. If none was given,
it displays the authenticated reporter's email only to reviewers holding
`reports.triage_listingreport`; no public or seller surface receives either
contact value.

## Security, privacy, and abuse controls

The application never stores a raw IP address. It normalizes and HMACs the
address with `REPORT_RATE_KEY_SECRET`; production settings fail closed when
that secret is absent. Reports are durably limited over a configurable window
by source hash, listing, and authenticated reporter. A short-lived duplicate
fingerprint suppresses repeated equivalent submissions.

The queue locks a report row during a transition, writes an audit action in the
same transaction, and does not call listing lifecycle services. Django admin
is read-only for report records and actions.

There are no automatic listing-status changes, reporter notifications, evidence
uploads, or reporter-facing report history. Retention remains pending the
separate proposal and records are not deleted by this feature.

## Migration, observability, rollout, rollback

Migrations `reports.0001_initial` and `reports.0002_alter_listingreport_options`
add the isolated report tables and permission. Configure
`REPORT_RATE_KEY_SECRET` before production deployment; rate settings have safe
bounded defaults but may be tuned through environment configuration. The
management console exposes a permission-gated queue link and bounded state
metrics. Rollback is application-level only while reports exist; do not remove
these additive tables without an approved retention decision and migration.

## Tests and acceptance criteria

Tests cover anonymous and authenticated submissions, no raw IP storage, CSRF,
nonpublic generic receipts, duplicate/rate suppression, unique queue controls,
safe reviewer links/contact fallback, queue permissions and feedback, locked
staff transition audit, append-only action behavior, and the public-to-staff
Playwright path. The feature is accepted when a report never changes a listing
automatically, cannot disclose report data through public/seller surfaces, and
every triage transition has an audit record.
