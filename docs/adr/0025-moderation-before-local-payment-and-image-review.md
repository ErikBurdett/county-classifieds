# ADR-0025: Moderation before local payment and per-image review

**Status:** Accepted  
**Date:** 2026-08-03

## Context

The local billing demo previously sent eligible Autos listings to payment before
staff review. That creates payment work for listings that may be rejected and
does not let moderators decide which submitted images can be public.

## Decision

Every seller submission enters moderation before a payment request. A moderator
can publish without payment, or approve a listing for the local payment link.
The latter moves the listing to `awaiting_payment`; a durable, confirmed local
payment automatically publishes that already-approved listing.

The DEBUG-only local payment amount is $10 for the primary county plus $5 for
each additional county, for every vertical, category, and In Search Of listing.
It remains server-owned demo configuration, not a production pricing policy.

Each image has storage state and an independent moderation state. Only
moderator-approved images may render publicly. A positive listing outcome
requires the category's approved-image minimum; otherwise the listing moves to
changes requested. On a material edit, existing approved images retain their
approval and newly uploaded or replaced images require review.

## Consequences

The existing local provider still does not contact Stripe. Production Checkout,
webhook verification, and pricing require a separate approved provider slice.
Payment approval, image decisions, notifications, and public visibility must
remain transactional, server-owned, auditable, and idempotent.
