# Open Decisions Register

Do not bury these choices in code. Resolve P0 items before the dependent milestone reaches implementation.

## P0 — blocks core design or launch

| ID | Decision | Recommended provisional default | Blocks |
|---|---|---|---|
| DEC-001 | Account integration with existing CountyPost properties | **Accepted 2026-07-23:** Separate marketplace custom user model at launch; preserve future OIDC/SSO adapter | M1 |
| DEC-002 | Approved state/county source and network-active flag owner | **Accepted 2026-07-23:** U.S. Census 2025 National Counties Gazetteer dataset; import all records; marketplace staff own separate active/network-enabled flags. See ADR-0010. | M2 |
| DEC-003 | Phone verification provider and consent copy | **Deferred:** not required for public listing reports or the local/demo seller workflow; resolve before production seller-submission eligibility is enabled. | M1 |
| DEC-004 | Refund policy for rejected paid listings | **Accepted 2026-07-23:** Staff rejection of a paid listing creates an automatic, full, durable and idempotent refund through the configured payment adapter. Local demo adapter support is implemented; Stripe implementation remains required for production. | M6/M12 |
| DEC-005 | Prohibited-items policy and escalation owner | **Accepted 2026-07-23:** Policy version 1, owned by project owner; prohibit weapons/firearms, controlled substances, adult services, financial/crypto offers, scams, stolen/counterfeit goods, and trafficking/exploitation; escalate suspected illegal activity to staff. See ADR-0013. | M5/M12 |
| DEC-006 | Material edit policy | **Accepted 2026-07-23:** Title, description, price, category, location, images, and structured details return listing offline to moderation. See ADR-0015. | M8 |
| DEC-007 | Community Board launch requirement | **Deferred post-launch:** Community Board is not a launch vertical; revisit after moderation capacity, UX, and policy are approved. | M3/M12 |
| DEC-008 | Verified CountyPost brand source/assets | Obtain live/design access, logo, fonts, colors, and representative screenshots; do not guess | M10 |
| DEC-009 | Production availability/recovery targets | **Accepted 2026-07-23:** RTO 4 hours, RPO 24 hours, and encrypted single-AZ RDS with tested automated-backup restores. See ADR-0017. | M11 |
| DEC-010 | Legal documents and consent versions | **Accepted 2026-07-23:** Project owner is approval owner for draft terms, privacy, refunds, prohibited items, communications, and content-rights documents. Named legal entity and counsel review remain launch blockers before production activation. | M12 |

## P1 — required before the affected feature

| ID | Decision | Recommended provisional default | Feature |
|---|---|---|---|
| DEC-101 | Email verification requirement | **Deferred:** not required to submit an optional private report email; resolve before sensitive-account verification policy changes. | Accounts |
| DEC-102 | Listing photo minimum exceptions | **Accepted 2026-07-23:** Per ListingKind/category policy; no universal hard-coded minimum. Required counts are enforced at future submission, not draft save. | Listings |
| DEC-103 | Price modes | **Accepted 2026-07-23:** Autos supports fixed price, negotiable, and contact-for-price. Free is not allowed for Autos. See ADR-0011. | Listings/search |
| DEC-104 | Exact address visibility | **Accepted 2026-07-23:** Exact Home/Rental street/unit/postal data is private by default and is included in public display, a lazy Google Maps iframe, or a user-initiated Google Maps URL only after seller opt-in. All other map actions use only city/county/state; no coordinates or general-area free-text query. The iframe is a disclosed third-party Google request when it loads. | Listings/privacy |
| DEC-105 | VIN handling | Store restricted; never public; define encryption/support visibility | Autos/security |
| DEC-106 | Renewal grace and re-moderation | **Accepted 2026-07-23:** One unchanged renewal paid within seven days after expiration bypasses full moderation; material edits always require review. See ADR-0015. | Renewal |
| DEC-107 | Featured start/refund during moderation or suspension | Starts on activation; paused/refund behavior defined in terms | Billing |
| DEC-108 | Sold listing public retention | **Accepted 2026-08-04:** Sold listings remain visible only on their seller's public profile for 30 days, with a Sold badge. They remain excluded from global browse and search; after retention they are not publicly listed. | Listing lifecycle |
| DEC-109 | Report-a-listing launch mechanism | **Accepted 2026-07-23:** Anonymous monitored in-product reports for presently public listings, with optional authenticated reporter/private email, staff-only triage, no automatic listing action, and a separate pending retention decision. See `features/RPT-001-public-listing-reports.md`. | Trust |
| DEC-110 | Exact email reminder schedule | Configure from product policy and measure fatigue | Notifications |
| DEC-111 | Staff MFA implementation | Approved MFA package or external identity/access layer | Security |
| DEC-112 | IaC tool | **Accepted 2026-07-23:** Terraform, with variable-driven configuration and externally configured encrypted remote state. See ADR-0017. | Infrastructure |
| DEC-113 | Generic local-demo placement pricing | **Accepted 2026-07-23:** $10 primary county plus $5 per additional county is DEBUG-only demo configuration; it is independent of item price mode and does not block moderation. See ADR-0019. | LST-009 |

## Accepted follow-up decisions

- **DEC-115 — Wanted/ISO temporary lifecycle and media policy:** **Accepted
  2026-07-31.** Wanted listings honor the current media requirement of their
  target category and have no expiration until a later accepted policy changes
  that behavior. See ADR-0024 and LST-011.
- **DEC-116 — Local moderation/payment sequence and demo placement price:**
  **Accepted 2026-08-03.** Every listing is moderated before any local payment
  request. Moderators may publish without payment or send a local payment link;
  a confirmed local payment publishes the approved listing. The DEBUG-only
  amount is $10 for the primary county plus $5 per additional county across all
  verticals, categories, and Wanted listings. Production Stripe pricing remains
  unresolved. See ADR-0025.
- **DEC-117 — Initial marketplace sponsored-ad workflow:** **Accepted
  2026-08-03.** Mirror County Post's deployment-managed static creative catalog
  and partner directory. Creatives are reviewed and copied into marketplace
  static assets; no self-service sales, tracking, targeting, or billing is
  introduced. External partner links open with `noopener`, `noreferrer`, and
  `sponsored`. See ADV-001.

## P2 — Phase 1B/later

- Saved-search immediate versus digest frequency and consent.
- Wanted/ISO production pricing and any replacement expiration policy.
- Messaging contact-redaction behavior and limitations.
- Messaging attachments, moderation access, deletion, and retention.
- Blocking semantics.
- Rating eligibility, direction, appeals, removal, and anti-retaliation.
- Dealer plan pricing, limits, staff, feeds, storefronts, and compliance.
- SMS provider, quiet hours, STOP/HELP handling, and cost controls.
- DEC-114 — **Accepted 2026-07-23:** The local-demo county browse rail may use
  public U.S. Census county internal points, with a 10–250 mile adjustable
  county-to-county estimate. It is not user, seller-address, ZIP, or listing
  radius search. Large/irregular county precision is intentionally limited.
  See ADR-0020. (M7 local demo)

## Decision process

For each decision:

1. State the user/business problem.
2. List options and operational consequences.
3. Include security, privacy, accounting, legal, and migration impact where relevant.
4. Select an owner and deadline.
5. Record the outcome in an ADR or product-decision record.
6. Update roadmap, feature specs, tests, and user-facing copy.
