# M12 — Staff Management Console

**Status:** Implemented locally  
**Milestone:** M12  
**Last updated:** 2026-07-23

## Problem and scope

Staff need one branded, low-risk starting point for moderation, billing
reconciliation, outbox recovery, policies, catalog, and geography without
duplicating the established domain workflows or exposing operational details to
seller accounts.

The `/manage/` namespace provides a staff-only login, logout, and aggregate
dashboard. It links only to existing moderation, billing, and Django admin
workflows. It contains no direct domain mutation controls.

## Actors and authorization

- Any `is_staff` user may authenticate to the console and view aggregate health
  totals.
- Each operational link requires the relevant existing permission. For example,
  moderation requires `listings.moderate_listing`; billing reconciliation
  requires `billing.view_order`; Django admin links require the target model's
  `view` permission.
- The console does not seed groups or grant permissions to arbitrary staff.
  Administrators must assign least-privileged model permissions or existing
  groups through Django admin.

## Behavior and safety

- Staff login reuses the marketplace user/session system but accepts only active
  staff users. Invalid credentials and valid non-staff credentials receive the
  same generic error. A rejected attempt clears any existing session.
- `next` accepts only a same-host, scheme-safe target; otherwise the user goes
  to `/manage/`.
- Anonymous console access redirects to the staff login. Authenticated
  non-staff users are signed out and redirected to that login.
- Login and logout are CSRF-protected browser forms. The dashboard exposes
  counts and oldest outbox age only: it does not include payment data,
  moderation notes, outbox payloads, or other freeform internal content.
- Dashboard queries are bounded aggregates. It does not load listing or order
  collections into memory.

## Data, observability, and operations

No model or migration is introduced. The dashboard reads current Listing,
Order, OutboxEvent, PolicyDocument, catalog, and geography records through one
read-model selector.

`seed_demo_staff` is DEBUG-only and creates `admin@local.test` only if it does
not exist. Its generated credential is recorded in ignored
`tmp/test-accounts.txt`; command output never prints the password. An existing
account with that email is left unchanged.

## Tests, rollout, and rollback

Tests cover staff/non-staff authentication, CSRF, safe redirects, aggregate
query budget, permission-aware navigation, billing authorization, seed
idempotency, password-output safety, and a Playwright staff-login flow.

Roll back by removing the `/manage/` URL include and console app. Because this
feature has no migration or durable state, rollback does not require a data
operation. The local demo account is intentionally not deleted by rollback.
