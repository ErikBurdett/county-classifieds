# TheCountyPost Market — Development Report

**Updated:** 2026-08-04
**Environment:** local Django 5.2 / Python 3.13 / PostgreSQL 18

## Current status

### 2026-08-04 public seller profiles, fulfillment, and seller-history retention

Active sellers now have immutable UUID public profiles with public listing
attribution, approved avatars, bios, HTTPS social/website links, member-since
data, public-history metrics, and public state/county coverage. Profile edits
create a pending `SellerProfileRevision`; Django Admin review selects one
approved revision while preserving the prior approved public content. Public
profiles never render email, phone, verification state, drafts, review records,
or rejected listings.

`Listing` now records first-publication and sold-retention timestamps. A sold
listing remains visible only on its seller's profile for 30 days, is labeled
Sold, and remains excluded from global browse/search/sitemaps. The
`clear_expired_sold_publication` command clears elapsed retention timestamps.
All listing workflows also carry independent pickup, delivery, and shipping
availability flags. `listings.0021`/`0022` and `accounts.0004`/`0005` were
applied locally.

### 2026-08-03 static sponsored advertising

`apps.advertising` provides a deployment-managed creative catalog, safe
external-link attributes, `/partners/`, inline/banner slots, compact sponsors,
and in-feed ads. In-feed ads use a responsive 300:250 contain layout so source
assets remain fully visible on all card grids. There is no self-service ad
sales, targeting, tracking, or advertising billing.

### 2026-08-03 moderation, local payment, image review, and notifications

Seller submission now always enters staff review before payment. Moderators can
publish immediately with **Approve Without Payment Link**, or approve a
DEBUG-only local-demo payment action. The latter snapshots a server-owned
$10 primary-county plus $5-per-additional-county order for every listing type,
including Wanted; a durable local payment confirmation publishes the already
approved listing.

Every stored image now has an independent review state. Only approved images
are public, rejected images remain private with seller-visible feedback, and
the category's approved-image minimum gates positive outcomes. Existing ready
images are backfilled as approved; later material edits preserve approval for
unchanged images and make newly uploaded/replaced images pending.

`apps.notifications` provides recipient-scoped, idempotent notification records,
an unread header bell, feed, mark-read controls, and server-allowlisted
same-origin destinations. Lifecycle, payment-ready, payment-complete, and
selected status events create seller-safe records while the existing outbox
remains the separate email side-effect boundary. Production Stripe, webhooks,
and provider pricing remain intentionally out of scope.

### 2026-07-30 Others overflow vertical

The versioned catalog now includes active `Others` with one seed-owned internal
`General` generic leaf. Unified create resolves General from the vertical on the
server for both JavaScript and no-JavaScript flows, hides the meaningless category
selection, and requires one existing bounded seller tag. After approval, public
cards/details present the classification as Others plus tags; existing public FTS
and SQLite fallback include those tags only through the established visibility
selector. The DEBUG fixture adds a safe Others example without a secondary
controlled tag. This is an overflow taxonomy, not a prohibited-content or
moderation exception. No migration, backfill, index, or new filtering surface is
required; final verification is recorded in `VALIDATION.md`.

### 2026-07-30 create-listing UX refinement

Unified create/edit now groups required work and optional native disclosures
without removing no-JavaScript fields. Authenticated same-origin typeahead
comboboxes search active state/territory and state-scoped county references,
synchronize native select values, and do not submit on selection. Inactive
locations are excluded; ZIP verification, additional counties, typed/generic
workflows, tags, broker gates, and moderation rules are unchanged. `make check`
passed (276 tests, 6 skipped, 85.14% coverage) and `make test-e2e` passed (22
Chromium tests). No migration, data backfill, external provider, or privacy/policy
change was made.

### 2026-07-30 local generic taxonomy demo and FTS rebuild slice

The DEBUG-only `seed_demo_generic_taxonomy` command now creates six bounded,
synthetic published generic exemplars across Services, Business & Industrial,
Jobs, Collectibles & Art, and Electronics. They exercise primary leaves,
same-vertical controlled tags, seller tags, safe additional facts, generic
profiles, the existing demo approval audit, public detail presentation, and
directory search. Pets and Home & Garden remain excluded because their current
workflow resolution is typed; no workflow policy changed. The seed uses only a
stable local seller and its own synthetic ZIP-to-county candidate, is
idempotent/non-destructive, and never makes custom-fact values searchable.
`rebuild_listing_search_documents` now preloads its taxonomy and generic-profile
relations per bounded UUID batch to prevent seed-scale N+1 behavior. No
migration, index, production-policy, or security-boundary change is required.

### 2026-07-30 SRCH-004 typed public browse filters

Public browse now offers vertical-scoped, typed controls for the existing Home,
Rental, Farm & Ranch equipment/pasture, Livestock, and Home Goods/Appliances
presentations; Autos retains its established controls. The server constructs a
validated per-vertical allowlist and maps values only to fixed typed lookups.
Cross-vertical, arbitrary, tag, generic-profile, and custom-fact parameters
are discarded before query construction and never propagate to chips, reset,
pagination, or live-fragment URLs. The established public selector, county
scope, nearby rail, FTS/relevance behavior, canonical/noindex rules, and
no-JavaScript/mobile accessibility path remain the boundary. No migration,
index, data backfill, or security-policy change was required. Local verification
passed `make check` (268 non-browser tests passed, 6 skipped, 19 browser tests
deselected, 85.24% coverage) and `make test-e2e` (19 Chromium tests passed).

### 2026-07-30 unified listing edit slice

The seller dashboard now resolves every listing to a unified private owner detail
and one `/dashboard/listings/<uuid>/edit/` route. That route locks the listing,
checks the active owner and allowed lifecycle status, and resolves the persisted
primary category/workflow server-side. It updates existing typed detail rows or
the existing bounded generic/profile row only; it cannot switch representations
or create a second detail model. It also replaces ADR-0023 controlled tags,
seller tags, and bounded facts, and applies the existing broker eligibility,
ZIP/county, material-edit, and moderation behavior. Published edits move offline
to `in_review`; custom facts remain absent from public templates until approval.
Legacy typed edit endpoints remain compatible protected workflows. Final command
evidence is recorded in `VALIDATION.md`.

### 2026-07-30 LST-010 seller workflow hardening

The category advance is now a non-persistent form transition: JavaScript
selection and ordinary **Show fields** submit the same server path, bind the
resolved typed or generic/profile form, and retain workflow-eligible title,
description, location, county placement, price, private address, broker, tag,
and fact inputs. It does not accept cross-vertical fields or create a draft.
Dashboard creation links, owner-detail edit links, and authenticated public owner
links now use the canonical unified routes. The owner detail distinguishes the
primary category from secondary controlled tags and consistently labels seller
values and broker/profile state as private or pending. No migration, backfill,
index, or policy change is required; final command evidence is recorded in
`VALIDATION.md`.

### 2026-07-29 bounded seller taxonomy and facts

ADR-0023 permits a deliberately narrow relational extension to LST-010: a
canonical primary category, same-vertical controlled leaf tags, up to ten
normalized seller tags, and up to eight normalized label/value facts. Seller tags
and facts stay private during draft/review, material edits return a publication to
review, approved tags join the public FTS document, and approved facts render only
as Additional details. This does not add arbitrary tag filtering, custom-fact
search/filter/sort, contact fields, automatic moderation, or provider integration.
Migrations `listings.0017`/`0018` are additive and require no backfill.

### 2026-07-29 LST-010 category and profile completion

Create Listing now returns and accepts only active postable leaf categories.
Group records remain taxonomy context and childless `Other` records remain
postable; each leaf label includes its vertical and parent-group context.
The same selector backs the server form, JSON enhancement endpoint, and
no-JavaScript submission error path. Catalog profile v2 now has 102 active
generic profiles with 668 controlled safe public supplemental-field definitions;
the local rerun retains 17 historical active fields. The 69 typed leaves
continue to use their existing detail forms and their retained historical
profile rows are inactive. The DEBUG local seed is idempotent and does not
delete unknown profile fields or stored attribute values. Final command
evidence is recorded in `VALIDATION.md`.

### 2026-07-29 approved broker attribution slice

Homes, Rentals, and Farm & Ranch listings now support one optional, normalized,
public `Listing.broker_name` (120 characters). The server-only category resolver
offers the **Broker or brokerage** field only in those eligible typed and generic
workflows; forged values for other verticals are rejected. It is a plain public
fact only—there are no broker contact fields, person records, licenses,
verification claims, links, map/FTS/filter use, or social/staff/policy output.
Changing it on a published listing uses the existing material-edit moderation
transition. `listings.0016` is additive and requires no backfill; final local
verification is recorded in `VALIDATION.md`.

### 2026-07-29 LST-010 unified dynamic listing creation

The authenticated dashboard now directs sellers to one full-page category-resolved
creation flow. It uses existing typed detail models for the approved typed
workflows and a seed-owned bounded JSON profile only for catalog-only supplemental
facts. Category groups are not postable unless childless; selected leaf categories
are persisted. `catalog.0008` and `listings.0015` are additive, with no backfill.
Profile values are allowlisted, escaped, visibility-scoped, and only explicit
public-search values enter search documents. Full quality/e2e evidence remains to
be recorded after the migration and browser seed are exercised.

### 2026-07-29 SRCH-003 PostgreSQL browse search

Added the accepted PostgreSQL `SearchVectorField`/GIN public-search document,
an explicit bounded rebuild command, and a SQLite fallback for the existing
test/browser path. County route context now defaults to statewide inventory;
the validated `scope=county` option includes primary and additional placements.
The document allowlist excludes seller, address, VIN, moderation, billing,
coordinates, and media/storage information. Feature deployment requires schema
migration followed by `make rebuild-listing-search-documents`; plan evidence is
recorded only when the local nationwide seed is available.

### 2026-07-27 RPT-001 workflow hardening

The existing public report flow now keeps its generic, CSRF-protected receipt
while the staff queue renders independently prefixed report forms, safe
public-listing/moderation-queue links, and reviewer-only reporter-contact
fallback. Triage uses explicit PRG feedback for successful, invalid,
closed/stale, missing, and unauthorized outcomes. No report schema or migration
was added; raw IPs, seller/public report disclosure, automatic listing action,
reporter notifications, evidence uploads, and retention/deletion policy remain
out of scope.

### 2026-07-27 submission/moderation repair

The seller flow now permits edits and private-media changes in `draft` and
`changes_requested`, then reuses the existing locked submission and moderation
services. Current active listing policies are presented with title, version,
and a same-origin document link; an owner-only CSRF-protected confirmation
records acceptance and submits atomically. No lifecycle schema or migration was
added. `awaiting_payment` remains a private DEBUG local-demo boundary, and
`in_review` is not public.

The local/demo foundation now spans M8–M12. It has the nationwide Census
directory, 18-vertical catalog, typed listings, generic private media,
moderation/lifecycle, deterministic local billing, outbox operations, public
multi-vertical browse/detail/media, SEO/accessibility foundations, Terraform
foundation, and a read-only staff management console.

This is not production-ready or a public launch. Local/demo implementation
must not be confused with production providers, legal approval, staffed
operations, or a deployed AWS environment. The concrete launch blockers are
listed in [Production and launch blockers](#production-and-launch-blockers).

## Implemented

### Foundation and operations

- Django modular monolith with split settings, UUID email-first user model,
  Argon2 passwords, request IDs, health endpoints, templates, semantic County
  Post tokens, Docker image, PostgreSQL Compose, CI, Ruff, mypy, pytest,
  Playwright smoke testing, dependency audit, and `uv.lock`.
- Docker Desktop support on WSL through Make targets that prefer `docker.exe`
  when it is available.
- Liveness: `/health/live/`; readiness: `/health/ready/`.
- M11 Terraform foundation for ECR, Fargate web/worker/operations tasks,
  private S3, optional CloudFront OAC, encrypted single-AZ RDS, logs/baseline
  alarms, EventBridge commands, and manual OIDC deployment. No AWS resources or
  credentials have been provisioned or committed.
- Production settings now fail closed for host/CSRF, database, S3, and SMTP
  requirements; private production media uses S3. Terraform validation is an
  additive CI job and does not alter existing Python/browser/container jobs.
- Staff-only `/manage/` management console with a separate staff login/logout,
  aggregate lifecycle/queue/reference-data health totals, and
  permission-aware links into existing moderation, reconciliation, policy,
  catalog, geography, and outbox workflows. It has no duplicate domain actions
  or payment/internal-note overview content. `make seed-demo-staff` creates the
  DEBUG-only `admin@local.test` account and records its credential only in
  ignored `tmp/test-accounts.txt`; it never changes an existing matching user.

### Accounts and private seller access

- Separate marketplace user identity (ADR-0008).
- Seller profile with display name, optional phone, and explicit unverified or
  verified state. No phone provider or verification process exists.
- Browser registration at `/register/`, login at `/login/`, CSRF-protected
  logout, seller profile editing, and private dashboard navigation.
- Registration creates the user and seller profile transactionally, signs the
  seller in, and does not honor untrusted redirect targets.
- Responsive shared navigation remains server-rendered: at 56rem and below a
  deferred same-origin Menu disclosure enhances the visible link baseline.
  Escape returns focus to the Menu button; link/form activation closes the
  disclosure without trapping focus. Active sellers keep Create listing visible
  outside the disclosure. No permissions, account routes, or authorization
  rules changed.

### Geography and catalog foundations

- `State` and `County` models with FIPS, normalized USPS/slug fields, active
  and network-enabled controls, admin, indexes, and PostgreSQL relationship
  protections.
- A checksum-validated, transactional U.S. Census 2025 National Counties
  Gazetteer importer with immutable provenance records, dry-run support, and
  idempotent non-destructive upserts. The local database has loaded the
  nationwide 2025 artifact: 52 state-equivalents and 3,222 counties.
- Geographic reference-data activity and public network participation are
  separate controls. The importer creates new records active and
  network-enabled, while staff may independently disable either control;
  reimports preserve existing flags. Per ADR-0012, active status alone governs
  public directory routes and the location finder; network-enabled status
  separately governs public inventory visibility.
- Lowercase canonical state/county directory routes resolve active records.
  Uppercase routes redirect to lowercase; unknown or inactive contexts return
  404. Active directory routes may intentionally be empty; sitemap/listing
  visibility applies the stricter active-and-network-enabled inventory policy.
- `Vertical` and `Category` models with active flags, ordering, admin, and
  PostgreSQL vertical/category integrity protections.
- Versioned marketplace taxonomy catalog covering 18 browse verticals with
  one-level category groups, generic Other categories, stable ordering, and
  searchable/filterable Django admin navigation. `make
  seed-marketplace-catalog` is DEBUG-only, idempotent, additive, and creates
  no listing kinds, products, price modes, or prices.
- The expanded taxonomy contains 19 verticals and 229 categories. Autos alone
  has a seller ListingKind/products and local billing configuration. The eight
  implemented typed presentations (Autos, Homes, Rentals, Agricultural
  Equipment, Livestock, Pasture, Home & Garden, and Appliances) are seeded as
  controlled public demos; this does not make non-Autos seller posting,
  products, pricing, or policy production-ready. Community remains non-postable
  vocabulary. Catalog-profile creation is locally implemented for generic leaves,
  but it does not establish production seller eligibility, payments, or launch
  policy.
- `ListingKind`, normalized supported price modes, server-owned listing
  products, and effective-dated product prices. PostgreSQL prevents overlapping
  `[start, end)` price windows for the same product/currency and rejects direct
  writes that would create free or zero-price Autos products.
- Catalog services resolve only an eligible active product and one
  effective-dated price at a supplied timestamp; inactive/unsupported,
  missing-price, and ambiguous-price cases fail closed with domain errors.
- DEC-103 is accepted: Autos supports fixed, negotiable, and
  contact-for-price modes, but not free (ADR-0011). The draft-only Autos form
  remains unchanged.
- Generic listing create/edit is a responsive, server-rendered form with
  state-first active-county discovery. It preserves county choices while the
  required ZIP is checked against imported offline HUD ZIP–county candidates;
  a missing import or ZIP candidate gives accessible feedback, while
  server-side validation still rejects unverified primary/additional counties.
  Its fixed/negotiable asking-price input accepts USD dollars and cents and
  converts them to stored integer minor units. No schema, policy, or Autos
  form behavior changed.
- Development-only idempotent seed command:

  ```bash
  make seed-texas-autos
  ```

  It creates Texas, Potter County, Randall County, Autos, its initial
  categories, and unpriced fixed/contact Autos product examples.
- The separate marketplace catalog seed preserves the established Autos
  vertical/category slugs while activating the broader browse taxonomy.

### Listings, lifecycle, and public browse

- Shared `Listing` aggregate with UUID identity, seller ownership, integer
  minor-unit price plus ISO currency, `draft`/`published` lifecycle, and typed
  one-to-one `AutoDetails`.
- `AutoDetails` keeps VIN private, normalizes it, and validates typed fields
  such as year, mileage, title status, and condition.
- Transactional draft services create/update only drafts. A separate locked
  transition service publishes complete Autos only when active catalog and
  active/network-enabled location records are present.
- Public home, state, county, and listing-detail pages use one visibility
  selector across all eight implemented typed presentations. Browse and detail
  pages display only public fields; VIN, seller email, exact private addresses,
  internal notes, and billing data are excluded.
- The public navigational design is complete for enabled/imported reference
  locations: the CountyPost-inspired home, state, and county pages use
  responsive square card grids, filter panels, and a reusable no-JavaScript
  market finder. The finder validates state/county pairs and sends valid
  selections to their canonical routes. It scales to any enabled Census
  reference records after import. The four-market Autos fixture is separate
  from the nationwide public demo inventory.
- A focused M10 local-demo UX hardening slice makes the home explicitly
  multi-vertical and keeps all active state links in a native collapsed
  directory after the market finder and fresh listings. Browse pages now expose
  a context-preserving reset link and a polite result summary; detail pages use
  contained responsive gallery cells (or an explicit no-image state) and
  separated save/report actions. Seller creation options are grouped and the
  empty dashboard provides a creation action. This is template/CSS-only:
  filters, visibility, favorite/report privacy, lifecycle, data, and migrations
  are unchanged.
- Public listing detail now has a lazy Google Maps iframe plus user-activated
  search and directions fallback links that open in a new tab. The iframe uses
  no API key or page-load JavaScript, has `referrerpolicy="no-referrer"`, and
  makes a third-party Google request when it loads. Destinations use
  city/county/state unless a Home or Rental seller explicitly opted into
  publishing an exact address; private street data, coordinates, and
  general-area text are never used as map queries. No production CSP is
  currently configured; before a restrictive CSP is activated, it must allow
  `frame-src https://www.google.com` while the iframe remains enabled.
- Public home, active directory, market-finder, and listing pages now derive
  title, description, canonical, Open Graph, and Twitter-card fields from one
  presentation layer. Clean route URLs are used for canonical and `og:url`;
  listing metadata reads only public title/city/state/route facts. A social
  image is emitted only for a ready processed public rendition, never an
  original/private/remote asset. County-equivalent metadata uses imported
  display names without inventing a `County` suffix. Browse-card and below-fold gallery images
  retain explicit dimensions and use processed endpoints with lazy loading and
  asynchronous decoding; no-image states remain visible. No JSON-LD is added.
- The market finder and state/county public browse controls retain ordinary
  server-rendered GET submissions and pagination, with a small deferred
  same-origin live-search enhancement for finder text and browse keywords/
  filters. Requests are bounded by the existing forms, abort stale searches,
  announce loading state, replace only result regions after success, and leave
  prior results intact on an error. Registration, seller forms, descriptions,
  and report inputs are intentionally outside this enhancement.
- At `45rem` and below, browse filters progressively enhance from an open,
  server-rendered form into an accessible disclosure. Validated active-filter
  chips, reset, and pagination URLs are generated only from allowlisted form
  values, preserving remaining state and selected nearby distance while
  excluding arbitrary request keys. Seller row actions and staff metrics/tools
  group into touch-friendly narrow layouts without changing lifecycle,
  permissions, SEO, or the nearby county-distance policy.
- County browse has a DEC-114 local-demo nearby rail: an accessible native
  10–250 mile GET slider defaults to 50 and returns up to 12 public listings
  from other counties, ordered by public Census county internal-point distance.
  It is explicitly approximate county-to-county distance—not user, seller,
  listing, ZIP, or address radius search—and it is omitted when the county
  lacks imported coordinates. It neither reads nor exposes private address,
  postal-code, or geocode data. The checksum-validated 2025 Gazetteer importer
  now idempotently imports `INTPTLAT`/`INTPTLONG` where available; a fixture
  without them safely leaves nearby unavailable. A coordinate-bearing local
  artifact must be imported to enable the rail.
- `make seed-demo-marketplace` remains a DEBUG-only, idempotent four-market
  Autos fixture. `make seed-nationwide-demo-inventory` is a separate DEBUG-only
  idempotent seed: the local nationwide import has 25,776 published demo
  listings (eight typed presentations × 3,222 counties). It uses synthetic
  local accounts and is neither launch inventory nor production content.
- Seller navigation uses the unified private routes:
  - `/dashboard/`
  - `/dashboard/listings/new/`
  - `/dashboard/listings/<uuid>/detail/`
  - `/dashboard/listings/<uuid>/edit/`
- Legacy typed and generic create/edit/detail routes remain protected
  compatibility workflows; they are not the canonical seller navigation.
- Owner checks return 404 for another seller's draft to avoid existence
  disclosure.

### M4 generic listing media
- Generic private `UploadSession`, `ListingImage`, and configurable
  ListingKind/category `ListingMediaPolicy` records support every typed draft.
  DEC-102 is accepted: no policy imposes a photo minimum, and required counts
  will not block draft saving.
- Local and test storage validates/decode-checks JPEG, PNG, and WebP uploads,
  re-encodes to metadata-free JPEG, derives a private preview, and keeps draft
  media private. Approved public listings can render processed media through
  the public selector. Production object storage remains fail-closed pending
  reviewed configuration.
- Owner-only media routes provide upload, numbered reordering, deletion, and
  private no-store/noindex delivery. `make cleanup-listing-media` idempotently
  expires abandoned sessions and stale local staging files.

### M5 submission and moderation
- Seller-owned typed drafts can submit atomically to `in_review`; form input
  cannot set lifecycle status or publication. Draft edits remain blocked once
  submitted.
- Staff with the explicit `listings.moderate_listing` permission use
  `/staff/moderation/` to approve/publish, request changes, reject, or suspend.
  Row locks and lifecycle revisions reject stale actions.
- Versioned reason codes and append-only moderation actions separate seller-safe
  explanations from internal notes. `make seed-moderation-reason-codes` is a
  DEBUG-only, idempotent local seed.
- DEC-005 is accepted in ADR-0013. The version-1 keyword scanner is advisory
  only; it flags review and never auto-rejects.

### Public listing reports
- DEC-109 is accepted for anonymous monitored in-product reports on presently
  public listings. The `reports` app stores optional authenticated reporter and
  private email, fixed reasons, bounded descriptions, HMACed normalized source
  addresses, durable rate-limit/duplicate evidence, state/assignment, and
  append-only actions.
- `/report-listing/<uuid>/` has CSRF-protected public intake and a generic
  receipt for successful, missing/nonpublic, duplicate, or rate-limited posts.
  Sellers and public surfaces cannot see report information.
- Staff holding `reports.triage_listingreport` use `/staff/reports/` to
  acknowledge, resolve, dismiss, or escalate under row locking. Queue forms use
  per-report prefixes, feedback is PRG-safe and generic, current public
  listings can be opened safely, and authenticated reporter-email fallback is
  visible only to authorized reviewers. These actions do not change a listing.
  Django admin exposes reports read-only and the management console link is
  permission-gated.
- Production requires `REPORT_RATE_KEY_SECRET`. Report retention is a proposal
  pending legal/product approval in `docs/RPT-001-REPORT-RETENTION-PROPOSAL.md`;
  no automatic deletion policy is implemented.

### M8 seller management, favorites, and renewal

- Listings now track expiration and material edits with `sold`, `expired`, and
  `archived` states. The public selector excludes expired timestamps before the
  future M9 scheduler.
- Owner-only POST actions support sold, archive, and restore-to-draft paths;
  material listing/detail/image edits depublish and return to review with audit.
- Authenticated visitors may favorite only public rows; saved-list reads apply
  the public selector again, preventing disclosure after a lifecycle change.
- Renewals are immutable orders with one pending renewal per listing. Accepted
  DEC-106 restores an unchanged listing paid within seven days after expiry,
  using the order-line duration snapshot. The local adapter remains DEBUG-only.

### Homes and Rentals private drafts

- `HomeDetails` and `RentalDetails` are typed one-to-one Listing details for
  the existing `real-estate` and `rentals` vertical slugs. Their separate
  transactional draft services lock listing updates, enforce ownership and
  draft-only state, and never publish.
- Typed fields include property/rental type, beds/baths, dimensions, dates,
  deposits, pets, and lease policy. PostgreSQL triggers prevent attaching
  incompatible detail rows or changing a listing vertical after any typed
  detail exists.
- Exact street address, unit, and postal code are private by default. Sellers
  may opt into future public display only after providing a street address;
  owner-only draft detail pages display their entered exact address. Public
  demos use only general-area location data.
- Private routes: `/dashboard/homes/new/`, `/dashboard/homes/<uuid>/`, and
  matching Rentals create, detail, and edit routes. The shared dashboard links
  to each private draft type.
- `make seed-demo-properties` is DEBUG-only, requires existing local demo
  sellers, and creates two bounded private drafts without altering existing
  drafts. Nationwide property publication waits for M5 moderation/submission
  and M7 public visibility/search policy.

### Rural private drafts

- `AgEquipmentDetails`, `LivestockDetails`, and `PastureDetails` are typed
  one-to-one details using the existing `farm-ranch` and `livestock-animals`
  catalog slugs. They collect equipment facts, general livestock sale facts,
  and pasture availability facts only; they do not collect serial numbers,
  animal health/testing or registration data, or exact property addresses.
- Fixed-vertical services lock draft updates, enforce ownership, and preserve
  draft state. PostgreSQL protections reject incompatible detail rows and
  vertical switches after rural detail creation.
- Private dashboard routes create, edit, and view each type. Public rural demos
  use the shared visibility, browse, detail, and media surfaces, but seller
  submission, products, and price flows remain Autos-only.
- `make seed-demo-rural-drafts` is DEBUG-only and idempotently creates one
  bounded private draft of each type for existing local demo accounts.

### Home Goods private drafts

- `HomeGoodsDetails` is a typed one-to-one detail model shared by the existing
  `home-garden` and `appliances` catalog slugs. It records a nonblank item type,
  optional brand/dimensions, and controlled condition, working-status, and
  pickup/delivery-preference values.
- Separate fixed-vertical services, forms, owner selectors, dashboard routes,
  and private templates create, edit, and display Home & Garden and Appliances
  drafts. PostgreSQL protections reject incompatible direct detail writes and
  switching a Home Goods listing to an unsupported vertical.
- `make seed-demo-home-goods-drafts` is DEBUG-only and idempotently creates one
  bounded private draft for each supported Home Goods vertical.

## Migrations applied locally

- `accounts.0001_initial` through `accounts.0005_sellerprofilerevision_avatar`
- `locations.0001_initial`, `locations.0002_county_state_fips_trigger`,
  `locations.0003_referenceimport`, `locations.0004_zipcountyreference`,
  `locations.0005_county_centroid_latitude_county_centroid_longitude_and_more`
- `catalog.0001_initial` through
  `catalog.0008_catalogpostingprofile_catalogpostingfield`
- `listings.0001_initial`, `listings.0002_relational_triggers`,
  `listings.0003_protect_auto_listing_vertical`,
  `listings.0004_remove_listing_listings_draft_status_only_and_more`,
  `listings.0005_homedetails_rentaldetails`,
  `listings.0006_agequipmentdetails_livestockdetails_pasturedetails`,
  `listings.0007_homegoodsdetails`, `listings.0008` through
  `listings.0022_listing_seller_feed_lifecycle`
- `billing.0001_initial` through `billing.0003_alter_order_status`
- `core.0001_initial`
- `policies.0001_initial`, `policies.0002_policydocument_policies_active_entity_required`
- `reports.0001_initial`, `reports.0002_alter_listingreport_options`
- `notifications.0001_initial`

All current migrations are additive. Generated PostgreSQL SQL has been
reviewed and the local PostgreSQL database migrates cleanly.

## Historical verification before the July 29–30 slices

Verified locally on 2026-07-27 for RPT-001 public reporting and reviewer
workflow hardening:

- `make check`: passed — Ruff formatting/linting, mypy (148 source files),
  Django checks, migration check with no changes, 222 non-browser tests passed,
  5 PostgreSQL-only tests skipped, 16 browser tests deselected, and 85.33%
  coverage.
- `make test-e2e`: passed — 16 Chromium browser tests (227 tests deselected),
  including the public listing report submission to authorized staff
  acknowledgement path.
- No migration was created. Security impact is limited to reviewer queue
  rendering and feedback: public eligibility, generic receipts, CSRF, HMACed
  source identifiers, report permissions, append-only audit records, and the
  no-automatic-enforcement boundary are preserved. Rollback is an
  application/template/test/documentation revert; existing report records and
  retention posture are unchanged.

Verified locally on 2026-07-27 for the M10 public SEO/social metadata and
image-layout-stability slice:

- `make check`: passed — Ruff formatting/linting, mypy (146 source files),
  Django checks, migration check with no changes, 217 non-browser tests passed,
  5 PostgreSQL-only tests skipped, 14 browser tests deselected, and 85.52%
  coverage.
- `make test-e2e`: passed — 14 Chromium browser tests (222 tests deselected).
  The 390px checks cover
  Menu and browse-filter disclosure/Escape/focus behavior, no-JavaScript
  baselines, chip/reset nearby-distance retention, seller actions, management
  tools, authenticated Create listing availability, and overflow guards.
- `uv run pytest --no-cov src/apps/core/tests/test_seo.py
  src/apps/listings/tests/test_m7_public_surfaces.py`: passed — 18 focused
  tests for public metadata privacy, canonical/Open Graph coherence,
  query/noindex behavior, county-equivalent naming, processed social-image
  eligibility, no-image state, and stable image attributes.
- No migration was created. Rollback is a presentation-layer, base-template,
  public-card/detail CSS/template, test, and documentation revert; routes,
  visibility selectors, permissions, and data remain unchanged.

Verified locally on 2026-07-24 for generic listing location, layout, and price
UX:

- `uv run pytest src/apps/listings/tests/test_generic_listings.py --no-cov`:
  passed — 6 focused generic-listing tests.
- `make check`: passed — Ruff formatting/linting, mypy (144 source files),
  Django checks, migration check with no changes detected, and 204 non-browser
  tests passed; 5 PostgreSQL-only tests skipped and 8 browser tests deselected;
  85.77% coverage.
- `make test-e2e`: passed — 8 Chromium browser tests.
- No migration was created. Rollback is a code/template/static-asset and
  documentation revert; imported HUD ZIP–county records and existing stored
  integer minor-unit prices are unchanged.

Verified locally on 2026-07-23 for the county-centroid nearby-listings rail:

- `make check`: passed — formatting, Ruff, mypy (144 source files), Django
  checks, migration check, and 201 non-browser tests passed; 5 PostgreSQL-only
  tests skipped and 8 browser tests deselected; 85.68% coverage.
- `make test-e2e`: passed — 8 Chromium browser tests, including the county
  nearby-distance slider GET path.
- Reviewed `sqlmigrate locations 0005` using the local PostgreSQL 18 compose
  database: additive nullable `numeric(8,6)`/`numeric(9,6)` fields, composite
  index, and latitude/longitude/pair constraints. Applied
  `locations.0005_county_centroid_latitude_county_centroid_longitude_and_more`
  successfully to that database.
- Rollback is a code rollback plus a forward migration if schema removal is
  required; populated public Census coordinates must not be deleted casually.

Verified locally on 2026-07-23 for the embedded public listing map:

- `make check`: passed — Ruff formatting/linting, mypy (138 source files),
  Django checks, migration check, and 190 non-browser tests passed; 5
  PostgreSQL-only tests skipped and 7 browser tests deselected; 86.59%
  coverage.
- `make test-e2e`: passed — 7 Chromium browser tests, including an assertion
  that the public listing-detail Google Maps frame exists.
- No migration was created. Rollback is a template/CSS/test/documentation
  revert; the third-party map request stops when the iframe is removed.

Verified locally on 2026-07-23 for public map actions and live search:

- `uv run python src/manage.py makemigrations --check --dry-run --settings=config.settings.test`:
  passed; no migration changes detected.
- `make check`: passed — Ruff formatting/linting, mypy (138 source files),
  Django checks, migration check, and 190 non-browser tests passed; 5
  PostgreSQL-only tests skipped and 6 browser tests deselected; 86.61%
  coverage.
- `make test-e2e`: passed — 6 Chromium browser tests, including live market
  finder and public browse keyword/filter result updates.
- No migration was created. Rollback is a code/template/static-asset revert;
  there is no persistent data change or third-party integration to disable.

Verified locally on 2026-07-23 after the local-demo readiness hardening slice:

- `make check`: passed — formatting, Ruff, mypy, Django checks, migration
  check, and 187 non-browser tests passed; 5 PostgreSQL-only tests skipped and
  5 browser tests deselected. No migration changes were detected.
- `make test-e2e`: 5 Chromium browser tests passed.
- The DEBUG-only `seed-demo-minimal` target now provides the bounded fresh
  local demo sequence. `seed-demo-full` adds only catalog/private-draft/draft
  policy fixtures; it does not import Census data, create media, activate
  policy, or run nationwide synthetic inventory.

Verified locally on 2026-07-23 after the M10 local-demo UX hardening slice:

- `uv run ruff format --check .` and `uv run ruff check .`: passed.
- `uv run mypy src`: passed with no issues in 137 source files.
- `uv run python src/manage.py check` and
  `uv run python src/manage.py makemigrations --check --dry-run --settings=config.settings.test`:
  passed with no issues and no migration changes.
- `uv run pytest -m "not e2e"`: 180 passed, 5 skipped, 5 browser tests
  deselected; 86.15% coverage.
- `DJANGO_ALLOW_ASYNC_UNSAFE=true uv run pytest -m e2e --no-cov`: 5 Chromium
  tests passed.

Verified locally on 2026-07-23 after the public-listing-reports slice:

- `make check`: 179 non-browser tests passed; 5 PostgreSQL-only tests skipped;
  5 browser tests deselected; 86.12% coverage.
- `make test-e2e`: 5 Chromium tests passed, including staff console sign-in.
- The latest record predates this documentation reconciliation. It is evidence
  of the local state then verified, not a claim that these documentation edits
  were re-tested.

## Production and launch blockers

### M1 account completion

- Email-verification policy and sensitive-account-change enforcement
  (DEC-101).
- Phone verification provider boundary, code expiry/attempts/rate limits, and
  consent handling (DEC-003).
- Production MFA approach (DEC-111) and any required production identity/access
  integration.

### Production payment and seller eligibility

- DEBUG-only local deterministic billing is implemented with durable Orders,
  OrderLines, PaymentEvents, immutable server-owned snapshots, replay, staff
  reconciliation, and a non-exposed FeaturedPlacement primitive.
- The approved `$10.00 USD` / 30-day Autos fixed-price configuration is seeded
  only by `seed_demo_billing`; it is explicitly not production pricing policy.
- Production Stripe Checkout, signed webhooks, provider reconciliation,
  production refunds, price mappings, and featured-entitlement policy remain
  absent or unresolved (DEC-107). There are no Stripe credentials or calls.
- Email verification, phone-provider/consent policy (DEC-003), and production
  MFA/identity-access integration remain incomplete.

### Production operations, legal, and launch

- No AWS resources, SES identity, DNS, ACM certificate, monitoring destination,
  production secrets, staging environment, or deployment/recovery rehearsal
  has been provisioned or demonstrated.
- Draft policy documents and local acceptance/refund flows are foundations only.
  A named legal entity and counsel review remain required before activation
  (DEC-010); no legal approval is claimed.
- M10 has implemented semantic UI, accessibility, and SEO foundations, but
  requires complete brand evidence, manual screen-reader review, production
  performance/crawl evidence, and launch-owner sign-off. The local first-party
  stylesheet manifest verifies only the tokens it records; no screenshot review
  or brand-parity approval is claimed.
- Staff training, launch inventory through normal audited flows, controlled
  rollout, and incident/support ownership are not complete.

## Active decisions and risks

- DEC-003: phone provider and consent copy remain unresolved; phone verification
  is deferred from public reports and remains required before seller submission
  eligibility is enabled.
- DEC-101: email verification is deferred from public reports; registration
  currently creates an active account.
- DEC-007: Community Board is explicitly post-launch and remains non-postable.
- DEC-102 and DEC-105 govern images and VIN security before public submission/
  publishing features. DEC-104 is implemented for private property drafts:
  exact addresses are collected privately and default to general-area public
  display unless a seller explicitly opts in. Public demo data does not expose
  exact addresses. DEC-103 is accepted for Autos only.

## Recommended next slices

1. Resolve seller-verification and production-payment decisions, then implement
   their production adapters and end-to-end controls.
2. Complete a real staging deployment, restore rehearsal, provider setup,
   monitoring/alarm ownership, legal review, staff training, and launch sign-off.
