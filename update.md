# TheCountyPost Market — Development Update

**Updated:** 2026-08-04
**Status:** Functional local/nationwide demo foundation; not ready for a public production launch.

## 2026-08-04 seller profiles, availability, retention, and sponsorship

- [x] Public seller profiles have stable UUID routes, safe listing attribution,
  approved avatars/bios/HTTPS links, state/county coverage, and public-history
  metrics. Pending profile revisions are reviewed in Django Admin.
- [x] Public profiles show active listings and Sold listings for 30 days only;
  sold listings stay out of global browse/search/sitemaps. Expired/archived
  rows are aggregate counts only.
- [x] Every listing can independently declare pickup, delivery, and shipping
  availability.
- [x] Static advertising now supplies `/partners/`, compact sponsors,
  banner/inline slots, and responsive in-feed ads without targeting, tracking,
  or self-service billing.
- [x] Seller submission now reaches moderation before any optional local-demo
  payment link. Image-level review and in-app notifications are implemented.

## 2026-07-30 Others overflow vertical

- [x] Added the active `Others` vertical and its sole seed-owned `General`
  generic leaf. Unified create resolves that leaf automatically without a visible
  category selector; Other listings require a bounded seller tag.
- [x] Public cards/details show `Others` and approved tags rather than the
  internal `General` leaf. Existing publication gates keep draft/review tags out
  of public search and display; no tag filter or sort was added.
- [x] The DEBUG-only generic taxonomy fixture now includes one safe Others
  example. Others is an overflow taxonomy only: prohibited-content rules and
  moderation remain unchanged.

## 2026-07-30 create-listing UX refinement

- [x] Unified typed and generic create/edit forms now use a compact numbered
  hierarchy with open native optional-detail disclosures, while retaining all
  fields and the no-JavaScript form controls.
- [x] Authenticated same-origin state/territory and state-scoped county
  candidate routes power keyboard-accessible typeahead comboboxes. Native
  selects remain the submission source and fallback; inactive locations are
  never returned. Selecting a location does not submit the form.
- [x] Changing state confirms before clearing selected placement. Existing
  server-side ZIP/county checks, additional-county picker, typed workflows,
  broker eligibility, tags, and catalog profiles are unchanged.
- [x] No migration, backfill, index, external lookup, privacy-policy, or
  moderation-policy change.

## 2026-07-30 local generic taxonomy demo and FTS rebuild

- [x] Added `make seed-demo-generic-taxonomy` and included it in
  `make seed-demo-full`. The DEBUG-only, idempotent fixture creates six
  synthetic published generic listings (Services, Business & Industrial, Jobs,
  Collectibles & Art, Electronics, and Others). Each has a primary leaf, seller
  tag, safe custom fact, and generic profile values; all except Others also have
  a controlled tag.
- [x] The fixture uses only a stable local seller and its synthetic
  ZIP-to-county candidate, publishes through the existing demo approval
  service, never deletes or updates user-owned data, and excludes Pets/Home &
  Garden because their current workflows are typed.
- [x] Seller tags are demonstrable through public FTS/SQLite fallback while
  custom facts remain detail-only. Search rebuild batches now preload taxonomy,
  generic profile fields, and details to prevent per-listing queries without
  changing document content or ranking.
- [x] No migration, index, production-policy, or security-boundary change.

## 2026-07-30 LST-010 seller workflow hardening

- [x] Category advance is now non-persistent and uses the same server-resolved
  typed/generic workflow for JavaScript and no-JavaScript submission. It retains
  all workflow-eligible common, placement, price, private-address, broker, tag,
  fact, and profile inputs while preventing cross-vertical values.
- [x] Dashboard creation, owner-detail edit, and authenticated public-owner edit
  links now use canonical unified routes. Owner detail distinguishes primary
  category from secondary controlled tags and labels pending seller values and
  broker/profile state consistently.
- [x] No schema migration, backfill, index, or policy change is required.

## 2026-07-30 SRCH-004 typed public browse filters

- [x] Public browse now renders only vertical-meaningful typed filters for
  Homes, Rentals, Farm & Ranch equipment/pasture, Livestock, and Home &
  Garden/Appliances; Autos filters and sorts remain unchanged.
- [x] A server-side per-vertical allowlist maps values to fixed typed lookups.
  Cross-vertical, arbitrary, tag, catalog-profile, and custom-fact parameters
  are ignored and never survive into active chips, reset/pagination/live URLs,
  or ORM field paths.
- [x] Existing public visibility, county scope/nearby rail, FTS relevance,
  canonical/noindex, ordinary GET, and mobile/no-JavaScript filter behavior
  remain intact. No migration, index, data backfill, or security-policy impact
  was introduced.

## 2026-07-30 LST-010 unified listing edit

- [x] One owner-only `/dashboard/listings/<uuid>/edit/` route now edits the
  persisted generic or typed representation through the server-resolved primary
  category/workflow; it cannot create or switch detail representations.
- [x] The route loads and persists typed/profile fields, eligible broker
  attribution, controlled tags, seller tags, and bounded custom facts under an
  owner row lock. `draft`, `changes_requested`, and `published` are the only
  editable statuses; a published material change moves the listing offline to
  review.
- [x] The dashboard now opens a unified private owner detail that labels pending
  tags/facts and broker attribution without leaking custom facts to public
  templates. Legacy direct typed edit URLs remain protected compatibility flows.

## 2026-07-29 SRCH-003 PostgreSQL browse search

- [x] Public browse uses a weighted, public-safe PostgreSQL FTS document and
  deterministic relevance-first ordering, with a bounded SQLite fallback.
- [x] County routes default to statewide scope; explicit county scope includes
  primary and additional placements without duplicates.
- [x] Search document rebuild is an idempotent batched operator command:
  `make rebuild-listing-search-documents`.
- [ ] Capture and record `EXPLAIN (ANALYZE, BUFFERS)` after migrating and
  rebuilding the locally available nationwide seed.

## 2026-07-29 LST-010 unified listing creation

- [x] The dashboard now has one Create Listing entry point with server-resolved
  typed or catalog-profile fields; legacy typed/generic URLs remain available.
- [x] Create Listing offers only active postable leaves; groups with active
  children cannot be selected or submitted, and leaf labels retain
  vertical/group context. Childless `Other` categories remain postable.
- [x] Catalog profile v2 uses reusable, safe field archetypes for all 102
  generic leaves (668 controlled field definitions). The 69 typed leaves use
  their existing typed forms and have no active generic profile. The local
  seed retains all 171 profile rows and 17 historical active fields without
  deleting unknown historical fields or values.
- [x] Additive catalog-profile and generic-attribute migrations plus an
  idempotent seed extension are present.
- [x] Applied `catalog.0008`/`listings.0015` locally, inspected PostgreSQL SQL,
  seeded 171 profiles, and passed `make check` (85.01% coverage) plus
  `make test-e2e` (17 Chromium tests).

## 2026-07-29 approved broker attribution

- [x] Homes, Rentals, and Farm & Ranch workflows offer an optional public
  **Broker or brokerage** name only, stored in additive
  `listings.0016_listing_broker_name`.
- [x] Server-side category validation rejects forged broker values outside those
  verticals; broker attribution remains a plain listing fact, not a contact,
  license, person-verification, map, search, social-metadata, or policy feature.
- [x] Inspected and applied the additive PostgreSQL migration locally; `make
  check` passed at 85.34% coverage and `make test-e2e` passed 17 Chromium
  tests. Exact evidence is recorded in `VALIDATION.md`.

## 2026-07-27 submission/moderation repair

- [x] Sellers can edit `draft` and `changes_requested` listings, manage their
  private media, and submit or resubmit through the existing lifecycle.
- [x] Active listing-policy documents are linked and require owner-only,
  CSRF-protected acceptance before the existing submission service proceeds.
- [x] The seller dashboard resolves each listing to its attached typed or
  generic detail page regardless of review status; `awaiting_payment` and
  `in_review` are explicitly private local-demo/review states.
- [x] `make check` passed: 219 tests passed, 5 skipped, and 14 browser tests
  deselected. `make test-e2e` passed: 15 Chromium tests.

## 2026-07-27 RPT-001 workflow hardening

- [x] Public report intake remains public-listing-only, CSRF-protected, and
  generic for accepted, hidden, duplicate, and rate-suppressed reports.
- [x] The permission-gated staff report queue uses uniquely prefixed CSRF forms,
  safe public/moderation links, reviewer-only reporter-contact fallback, and
  PRG feedback for triage outcomes.
- [x] Report triage does not change listing status. No reporter notifications,
  evidence uploads, or retention/deletion policy were added.

## Completed

### Marketplace and reference data

- [x] Django modular monolith with PostgreSQL, Docker, CI, Ruff, mypy, pytest,
  Playwright, health checks, request IDs, and production-shaped settings.
- [x] Nationwide U.S. Census 2025 geography: 52 state-equivalents and 3,222
  counties, active directory routes, canonical lowercase URLs, and FIPS
  integrity protection.
- [x] Census county internal-point coordinates imported locally for the
  county-to-county nearby-listings demo.
- [x] 19 verticals and 229 categories, including Pets, Jobs, Services, and the
  narrow Others overflow vertical with its hidden General leaf.
- [x] Versioned local HUD USPS ZIP–County Crosswalk importer with SHA256,
  release metadata, county-FIPS validation, dry-run, and idempotent upserts.

### Public experience

- [x] Responsive home, market finder, state pages, county pages, listing
  cards, listing details, filtering, sorting, pagination, reset controls, and
  accessible empty/error states.
- [x] Deterministic public SEO/social metadata for home, active state/county
  directories, market finder, and public listings: clean-route canonicals and
  Open Graph URLs, title/description, Twitter cards, and absolute social images
  only for ready processed public renditions. Metadata excludes query strings,
  private location/contact fields, coordinates, listing descriptions, and
  non-public media; county-equivalent names retain their imported display text
  without a fabricated `County` suffix; no JSON-LD is emitted.
- [x] Public browse cards and listing galleries reserve known image dimensions,
  use only processed public rendition URLs, and lazy-load/asynchronously decode
  non-critical images while retaining accessible no-image states.
- [x] Progressive live search for the public market finder and public listing
  browse controls, with loading announcements and ordinary GET fallback.
- [x] Lazy Google Maps iframe, map link, and directions link on public listing
  details. Exact street addresses are used only after a Home/Rental seller
  explicitly opts in; all other map destinations use city/county/state.
- [x] County feeds include a separate nearby-public-listings rail, adjustable
  from 10 to 250 miles. It uses public county internal points only, excludes
  the current county, and is an approximate county-to-county estimate.
- [x] Anonymous public listing reports with staff-only triage, duplicate/rate
  protection, and reporter privacy.

### Seller listing workflow

- [x] Account registration, login/logout, password reset, seller profile,
  account suspension enforcement, security audit events, and staff role
  provisioning.
- [x] Typed private draft workflows for Autos, Homes, Rentals, Agricultural
  Equipment, Livestock, Pasture, Home & Garden, and Appliances.
- [x] Universal bounded generic listing workflow for every active catalog
  category, including Pets, Jobs, Services, and Other.
- [x] Create Listing action in authenticated top navigation and directly below
  the seller dashboard heading.
- [x] Responsive full-width generic form with category filtering, state-scoped
  primary county live search, nearby-county tag picker, no-JavaScript
  fallbacks, private street address field, and USD asking-price input.
- [x] Mobile-first responsive/navigation refinement: a labeled 56rem Menu
  disclosure progressively enhances the server-rendered navigation, keeps
  no-JavaScript links usable, returns focus on Escape, and retains authenticated
  Create listing as a visible primary action. Browse, nearby rail, detail/map,
  seller/staff, generic form, messages, and footer now include narrow/tablet
  overflow and touch-target safeguards.
- [x] Mobile browse filters now have a no-JavaScript-open disclosure baseline,
  accessible enhanced toggle/Escape/error focus, and validated active-filter
  removal links. Reset retains a selected nearby county distance; clear-all
  returns to the market route. Seller row controls and management metrics/tools
  stack cleanly at 320–480px without changing public query, permission, or
  lifecycle behavior.
- [x] ZIP/FIPS verification is server-authoritative for primary and additional
  county placements. Seller choices are retained with accessible feedback when
  an offline crosswalk is missing or does not contain a ZIP candidate.
- [x] Generic local-demo quote: $10 primary county placement plus $5 per
  additional county. It is server-owned, recorded for the demo, independent of
  item asking price, and does not collect payment or delay moderation.
- [x] Generic drafts can submit into the existing local moderation workflow;
  typed draft workflows remain intact.
- [x] Private media upload, validation, re-encoding, ordering, cleanup, and
  public processed renditions for approved listings.

### Trust, lifecycle, billing, and operations

- [x] Seller submission, moderation queue, reason codes, advisory policy scan,
  append-only moderation actions, approval, rejection, changes requested, and
  suspension.
- [x] Favorites, sold/archive/restore actions, material-edit re-moderation,
  expiration safety, and local renewal boundary.
- [x] Durable Orders, OrderLines, PaymentEvents, local deterministic billing,
  staff reconciliation, and automatic local-demo refund support for rejected
  paid listings.
- [x] Transactional outbox, expiration/reminder commands, local email
  templates, delivery attempts, and operational inspection commands.
- [x] Staff management console, role groups, local demo staff seed, policy
  documents/acceptances foundation, Terraform foundation, OIDC deployment
  workflow, and launch/readiness runbooks.

### Demo data and verification

- [x] DEBUG-only idempotent demo seeds for staff, roles, Autos, nationwide
  inventory, catalog, billing, moderation reasons, typed private drafts, and
  generic local-demo pricing.
- [x] Nationwide synthetic demo inventory: 25,776 published records across
  the eight typed presentations and 3,222 counties. This is not production
  inventory.
- [x] Latest recorded application quality evidence (2026-07-30): `make check`
  passed with 279 non-browser tests, 6 PostgreSQL-only tests skipped, 23 browser
  tests deselected, and 85.15% coverage; `make test-e2e` passed with 23 Chromium
  tests, including the 390px Others workflow. This is historical local evidence;
  a future commit must rerun the gates after its final changes.

## In progress / local-demo boundaries

- [ ] Import the locally supplied HUD USPS ZIP–County Crosswalk in each demo
  environment before generic ZIP/county verification can succeed. HUD source
  access is operator-provided; the application does not make runtime external
  lookup requests.
- [ ] Generic county placement pricing is a local-demo quote/order foundation.
  It is not a production checkout, Stripe price, or approved production price
  policy.
- [ ] Public browse has locally implemented PostgreSQL weighted full-text
  search, state-default/county scope, and vertical typed filters. Featured
  placements and production query-plan/performance evidence remain incomplete.
- [ ] Nearby listings are a bounded local-demo county-centroid estimate, not
  true buyer, seller, listing-address, ZIP, or radius search.
- [ ] Google Maps is embedded on public details and is therefore a disclosed
  third-party request. A future restrictive CSP must permit the chosen
  Google frame origin.
- [ ] Accessibility, screen-reader, browser compatibility, performance, and
  brand evidence have automated foundations but still need formal review and
  sign-off.
- [ ] The mobile refinement has automated 390px browser coverage, but manual
  screen-reader and representative-device review remain required before launch.
- [ ] Terraform, CI/CD, private production media, outbox, and runbooks are
  implemented as foundations; no staging or production AWS environment has
  been provisioned.

## Remaining work before production launch

### Product, policy, and legal

- [ ] Select a phone-verification provider and finalize consent copy
  (DEC-003).
- [ ] Decide the email-verification requirement for sensitive account changes
  (DEC-101).
- [ ] Finalize VIN encryption/support-access policy (DEC-105).
- [ ] Define featured-placement activation, suspension, and refund behavior
  (DEC-107).
- [ ] Define public sold-listing retention (DEC-108) and reminder schedule
  (DEC-110).
- [ ] Approve staff MFA approach (DEC-111).
- [ ] Obtain named legal entity, counsel review, and approved active legal,
  privacy, refund, reporting, and consent documents.
- [ ] Obtain approved CountyPost brand assets/evidence and complete brand
  sign-off.
- [ ] Keep Community Board out of launch scope unless its moderation and
  policy requirements are separately approved.

### Providers and production integrations

- [ ] Implement Stripe Checkout, signed webhooks, replay, production refunds,
  and production price mappings.
- [ ] Configure SES, sender authentication, bounce/complaint processing, and
  EventBridge schedules.
- [ ] Configure production media upload/storage delivery and image operations.
- [ ] Provision reviewed staging and production AWS accounts, DNS, ACM,
  Secrets Manager, monitoring, and alarms.
- [ ] Perform a staging deployment, migration rehearsal, RDS restore exercise,
  rollback rehearsal, and launch smoke test.

### Operational readiness

- [ ] Add production payment/listing history and support surfaces where needed.
- [ ] Establish moderation, support, finance, and incident-response training.
- [ ] Decide and implement report-data retention after legal/product approval.
- [ ] Complete security review, load testing, manual accessibility review, and
  launch checklist sign-off.

## Useful local commands

```bash
make compose-up
make migrate
make seed-demo-minimal
make run
```

For generic ZIP/county verification, import an operator-supplied HUD crosswalk:

```bash
make import-hud-zip-counties \
  SOURCE=/path/to/ZIP_COUNTY.csv \
  SHA256=<file-sha256> \
  RELEASE_DATE=YYYY-MM-DD \
  RELEASE_VERSION=YYYY-QN
```

See `dev-report.md` for detailed implementation evidence, `docs/14-OPEN-DECISIONS.md`
for unresolved decisions, and `docs/19-LAUNCH-CHECKLIST.md` for launch tasks.
