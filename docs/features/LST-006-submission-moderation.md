# LST-006 — Submission and Moderation

**Status:** Implemented locally; production payment/provider workflow incomplete  
**Milestone:** M5

## Problem
Private drafts need a controlled, auditable path to publication without exposing unreviewed inventory.

## Scope and non-goals
Owners submit complete typed or generic drafts. Staff with
`listings.moderate_listing` review, approve without payment, approve and send a
local payment link, request changes, reject, or suspend listings. This includes
versioned reason codes, append-only action history, individual image decisions,
a deterministic advisory scanner, and a staff queue. Production Stripe,
restoration, archival, and automatic image moderation remain out of scope.

## Actors and behavior
- Owners may submit only their own `draft` or `changes_requested` listing. Server-side completeness checks validate common fields, compatible details, and the configured media minimum.
- Submission records `draft|changes_requested → submitted → in_review` atomically.
  The submitted state is recorded for audit. Seller submission never creates a
  payment-pending listing.
- Moderators require the explicit Django permission. An action uses the lifecycle revision and a row lock; stale reviews fail. Negative outcomes require an active reason code.
- Moderators may publish immediately or approve a listing for payment. The
  payment path changes to `awaiting_payment`, remains private, and a confirmed
  local payment publishes it without another review. Sellers see status, image
  feedback, reason guidance, and the optional seller-facing note only. Internal
  notes and scanner flags are staff-only.
- Moderators approve or reject each submitted image. Only approved images render
  publicly. A positive outcome that does not meet the category image minimum
  becomes changes requested.
- The existing `publish_auto_listing` remains a documented staff/demo fixture compatibility path. It records a system direct-approval action and is not exposed to sellers.

## State and data
`draft → submitted → in_review → published|awaiting_payment|changes_requested|rejected`;
`awaiting_payment → published` only after durable payment confirmation; and
`in_review|published → suspended`. `archived` and restoration are deferred.
`ModerationReasonCode` is stable/versioned and deactivated rather than deleted.
`ModerationAction` is append-only in application use and stores actor, state
pair, outcome, optional code, separated notes, and timestamp.

## Scanner, security, and privacy
The scanner uses case-insensitive word-boundary keyword matches in existing title/description data for the baseline prohibited categories. It only creates internal review flags; it never rejects, removes content, or claims legal certainty. It can have false positives/negatives and requires staff judgment. It adds no freeform-content logging. Status is not a form field, and all mutations enforce ownership or permission plus CSRF.

## Local-demo boundary

The implemented status names are `draft`, `submitted`, `awaiting_payment`,
`in_review`, `published`, `changes_requested`, `rejected`, and `suspended`.
All types move directly from `submitted` to `in_review`. A moderator may use
the DEBUG-only local payment path after review; its $10 primary-county plus $5
additional-county amount applies across the catalog and to Wanted listings.

## Migration, rollout, rollback
Migration `listings.0009` adds lifecycle data and audit tables, expands the status constraint while preserving existing `published` fixtures, and adds queue/history indexes. Seed `make seed-moderation-reason-codes` after migration for local version-1 data. Roll back application exposure first; the additive tables/columns can remain while an operational forward fix is prepared.

## Tests and acceptance
Tests cover owner submission and re-submission after changes requested,
incomplete/mismatched details, media policy, active-policy acceptance, scanner
boundaries, reason enforcement, permission checks, stale revisions, immutable
audit behavior, private seller rendering, and public selector exclusion.
Existing published Autos fixtures continue through the shared published-only
selector.
