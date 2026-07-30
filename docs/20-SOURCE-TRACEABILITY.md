# Source Traceability and Decision Boundary

## Purpose

The source document is an initial AI-assisted product conversation from a non-technical stakeholder. It is authoritative for product intent only where the document is explicit. It is not a final technical specification, policy set, legal review, estimate, or acceptance test.

This project keeps three categories separate:

1. **Source-derived requirement** — explicitly stated in the stakeholder document.
2. **Engineering decision** — selected for implementation and recorded in this kit/ADRs.
3. **Open product/policy decision** — not sufficiently defined and must not be silently implemented.

## Source-derived product requirements

| Area | Requirement captured from source | Engineering treatment |
|---|---|---|
| Positioning | A mid-to-high-end regional classifieds product; structured, moderated, and trusted; quality over volume | Product charter and moderation-first lifecycle |
| Deployment boundary | Independent application at `market.thecountypost.com` | Separate Django deployment and release path from news sites |
| Data topology | One marketplace and one shared listings database | One modular monolith and PostgreSQL database; no county tenancy/silos |
| Geography | Required state and county; state/county routes; statewide default with county toggle | Normalized reference tables, canonical lowercase routes, scope context |
| Launch footprint | Technically available network-wide; promotion/inventory starts in Potter and Randall | Network-active reference/config flag; seed strategy is operational, not deployment topology |
| Verticals | Homes, rentals, autos, ag equipment, pasture/cattle, appliances/home; separate Community Board | Explicit vertical/category catalog and typed one-to-one detail models |
| Listing quality | Structured required fields and photos | Per-kind/vertical policies; source’s universal minimum is treated as unresolved where it conflicts with Community/Wanted behavior |
| Trust | Pre-publish moderation, verified phone, profile/member-since | M1 identity/verification and M5 moderation; ratings deferred pending eligibility policy |
| Buyer retention | Favorites, saved searches/alerts | Favorites in Phase 1A; saved searches/alerts Phase 1B in the reduced scope |
| Communication | In-platform messaging with contact controls | Deferred to Phase 1B after abuse, retention, redaction, access, and deletion decisions |
| Wanted listings | Wanted/ISO in every vertical | Deferred to Phase 1B pending field/photo/price/expiry rules |
| Pricing | Community free/7 days; standard $10/30 days; selected high-value verticals $25/60 days; featured +$15; dealer plan TBD | Internal effective-dated products mapped to Stripe; amounts require stakeholder confirmation before live configuration |
| Payments | New TheCountyPost Stripe account; separate accounting streams | Stripe Checkout for listing fees/upgrades only; no buyer/seller money movement or Stripe Connect |
| Homepage | Brand/masthead, scope toggle, search, post action, category grid/counts, featured row, distinct Community strip | Component/route roadmap; exact brand values require verified evidence |
| Integration | Weekly county digest, Capital Income Properties, county site links, existing AWS | Digest Phase 1B; external integration contracts remain explicit work; AWS architecture in ADRs |
| Build priority | Routes/scope, listing creation/photos, moderation, browse/search, Stripe, phone verification, saved searches, messaging possibly 1b | Re-sequenced into release gates to reduce launch and payment/moderation risk |

## Engineering decisions introduced by this kit

These are not claims from the stakeholder source. They are recommended implementation choices and are recorded in the architecture/ADRs:

- Django 5.2 LTS on Python 3.13
- modular monolith
- server-rendered templates with progressive enhancement
- PostgreSQL 18 and PostgreSQL-native search first
- typed one-to-one vertical detail tables rather than EAV
- explicit lifecycle transition services and immutable history
- direct private S3 staging plus controlled image processing
- Stripe Checkout with webhook-only durable payment truth
- transactional PostgreSQL outbox and separate worker
- ECS Express Mode web deployment with RDS/S3/SES/Secrets Manager/CloudWatch
- WhiteNoise for application static assets initially
- separate marketplace custom user as a provisional identity default

An accepted ADR may supersede any engineering recommendation without rewriting the product source.

## Source conflicts or incomplete areas

Do not silently reconcile these:

- URL examples use inconsistent capitalization and one malformed brace; canonical lowercase paths are an engineering recommendation.
- The source says all counties are open at launch but one field table says county is “Potter/Randall.” Treat the latter as initial marketing/inventory, not a hard-coded data constraint, after stakeholder confirmation.
- A universal photo/price minimum conflicts with Community Board, Wanted/ISO, events, free items, and contact-price use cases.
- Ratings are promised without a completed-interaction eligibility/appeal/removal workflow.
- Messaging is promised without an enforceable definition of contact stripping, attachments, retention, moderator access, blocking, reporting, or deletion.
- Dealer/broker plans are named but not product-defined.
- Refund, renewal, rejection, suspension, and featured-entitlement behavior are incomplete.
- User integration with existing CountyPost accounts is not specified.
- Legal/privacy/prohibited-item/consent/retention policies are not supplied.

The authoritative list of decisions is `docs/14-OPEN-DECISIONS.md`.
