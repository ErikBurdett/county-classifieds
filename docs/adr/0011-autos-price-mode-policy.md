# ADR 0011: Autos Price-Mode Policy

**Status:** Accepted  
**Date:** 2026-07-23  
**Decision owners:** Project owner  
**Supersedes:** none  
**Superseded by:** none

## Context

Autos needs an explicit seller-facing price-mode policy before catalog products
or a future listing-submission flow can determine eligibility. A generic
free-price default would undermine the Autos marketplace policy and must not be
introduced accidentally through a reusable catalog.

## Options considered

### Option A — Fixed, negotiable, and contact-for-price; no free Autos

Autos sellers may select a fixed price, offer a negotiable price, or ask buyers
to contact them for a price. Autos cannot be offered as free.

### Option B — Allow free Autos

This would expand the listing modes with no approved operational or moderation
policy for free vehicle offers.

## Decision

Effective 2026-07-23, Autos supports exactly fixed price, negotiable, and
contact-for-price modes. Free is not an eligible Autos mode or Autos product
state.

## Consequences

- The catalog stores price-mode eligibility per listing kind rather than
  inferring it from a form or product label.
- Autos product definitions cannot be marked free and Autos price rows cannot
  have a zero amount.
- This decision does not alter the existing draft-only Autos form; integrating
  price modes with listing fields remains a later listing/submission slice.
- Other verticals require their own approved policy before free is enabled.

## Data and migration impact

Additive catalog tables record listing-kind supported price modes, products, and
effective-dated product prices. PostgreSQL constraints and triggers reject
invalid direct writes; application services fail closed when catalog records
are inactive, unsupported, missing, or ambiguous.

## References

- `docs/14-OPEN-DECISIONS.md` DEC-103
- `docs/features/CAT-002-003-listing-kinds-products-pricing.md`
