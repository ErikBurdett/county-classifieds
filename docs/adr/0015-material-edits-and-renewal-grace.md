# ADR-0015: Material edits and renewal grace

**Status:** Accepted  
**Date:** 2026-07-23  
**Decisions:** DEC-006, DEC-106

## Context

Published listings must remain trustworthy after seller self-service changes, while
an expired listing should not need unnecessary repeat moderation when its approved
content is unchanged.

## Decision

- Changing title, description, price, category, state/county/city, typed detail
  data, or ready images is material. A published listing is immediately removed
  from public visibility and moved to `in_review`; the owner edit and transition
  are audited.
- A renewal is a new immutable order. Exactly one pending renewal may exist for a
  listing. A paid renewal made no later than seven days after expiration restores
  the unchanged listing to `published` without full moderation.
- The renewed expiry is payment-confirmation time plus the immutable
  `OrderLine.duration_days` snapshot. Browser redirects never grant the
  entitlement.
- Missing expiry, an inactive/missing server-priced renewal product, a material
  edit awaiting review, or expiry outside the grace window fails closed and
  requires the normal moderated path.

## Consequences

The public selector independently excludes `expires_at <= now`, so stale inventory
is hidden before M9's scheduler exists. This decision adds no payment provider,
refund, notification, or background job.
