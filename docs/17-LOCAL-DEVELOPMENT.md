# Local Development Contract

## Desired developer experience

After bootstrap:

```bash
cp .env.example .env
make bootstrap
make compose-up
make migrate
make seed-demo-minimal
make run
```

A developer should not need an AWS account or Stripe live credentials to run core flows.
`seed-demo-minimal` requires PostgreSQL to be running and migrations to be
applied. It is DEBUG-only and idempotently seeds the Texas/Autos reference
fixture, bounded public marketplace sellers/listings, moderation reason codes,
the local Autos billing configuration, staff role groups, and the local
management-console superuser. It does not download Census data, enable
nationwide geography, call a provider, activate policy documents, or create
listing images.

## Exact local demo paths

All seed commands below require `DEBUG=True`, PostgreSQL running, and current
migrations. They are local/demo tools, not production bootstrap steps.

**Small bounded demo** — no operator-supplied data:

```bash
cp .env.example .env
make bootstrap
make compose-up
make migrate
make seed-demo-minimal
make run
```

**Full bounded seller/demo fixture** — extends the small demo with catalog
profiles, six generic public taxonomy examples (including Others), private typed
drafts, and draft policy placeholders:

```bash
make seed-demo-full
```

The full fixture also runs `make seed-demo-wanted-listings`: a DEBUG-only,
idempotent set of clearly synthetic Wanted examples. It reuses an existing
local demo seller, target category media policy, and the normal approval path;
it creates no real request or identity and has no expiration under DEC-115.

**Nationwide typed-search demo** — requires the operator to provide the Census
archive and checksum. Validate it first, then import, seed, and rebuild
PostgreSQL documents:

```bash
make import-census-geography \
  SOURCE=/secure/path/2025_Gaz_counties_national.zip \
  SHA256=<vendor-sha256> \
  RELEASE_DATE=YYYY-MM-DD \
  EXTRA_ARGS="--dry-run"
make import-census-geography \
  SOURCE=/secure/path/2025_Gaz_counties_national.zip \
  SHA256=<vendor-sha256> \
  RELEASE_DATE=YYYY-MM-DD
make seed-marketplace-catalog
make seed-nationwide-demo-inventory
make rebuild-listing-search-documents EXTRA_ARGS="--batch-size 250"
```

The rebuild command requires PostgreSQL; SQLite tests exercise the bounded
fallback instead. Capture representative `EXPLAIN (ANALYZE, BUFFERS)` evidence
separately—seed-scale output is not production performance evidence.

## Create-listing location refinement

The seller create/edit form needs no location-service credentials. Its optional
typeahead calls authenticated same-origin routes backed by active `State` and
`County` reference rows already loaded locally. Native selects remain available
with JavaScript disabled. Import active Census/HUD reference data before testing
a location not present in the local fixture; the form performs no network lookup.

## Account registration

With the local server running, visit `/register/` to create a seller account.
Successful registration signs the seller in and redirects to `/dashboard/`.

## Local public marketplace demo seed

After starting PostgreSQL and applying migrations, the same bounded local demo
can be seeded in one command:

```bash
make seed-demo-minimal
```

For individual troubleshooting, the working dependency order is
`seed-texas-autos`, `seed-demo-marketplace`, `seed-moderation-reason-codes`,
`seed-demo-billing`, `provision-staff-groups`, then `seed-demo-staff`. All are
DEBUG-only and idempotent. `seed-texas-autos` creates
the small Autos reference fixture; it does not download Census data or create
users.

`seed-demo-marketplace` is also DEBUG-only and idempotently creates four local
seller accounts and three published Autos listings in each of Texas/Potter, New
Mexico/Bernalillo, Colorado/Denver, and Oklahoma/Tulsa. It records local-only
test credentials in ignored `tmp/test-accounts.txt`; it never prints them.
Seed commands merge only newly-created deterministic accounts into this file,
preserve other account entries, and never alter an existing account's password
or privileges. If a password is unknown, reset it locally with
`uv run python src/manage.py changepassword <email>`; the password prompt is
interactive and does not echo the secret.
The public home, browse, and detail pages are multi-vertical surfaces; this
small seed remains an Autos-only fixture and is not a statement of production
inventory policy.

For the already-loaded nationwide local reference dataset, use:

```bash
make seed-marketplace-catalog
make seed-nationwide-demo-inventory
make rebuild-listing-search-documents
```

The nationwide demo seed creates one public exemplar for each of the eight
implemented typed presentations in every active, network-enabled county. The
recorded local run created 25,776 synthetic listings across 3,222 counties; it
is not launch inventory and must never be mistaken for production content.

On a state or county browse route, select a vertical before using its typed
filters. Homes, Rentals, Farm & Ranch equipment/pasture, Livestock, and Home
& Garden/Appliances expose only their relevant bounded controls; Autos keeps
its established controls. The filters use the public selector and ordinary GET
URLs, so no private listing, tags, catalog-profile attributes, or custom facts
become filterable. See `docs/features/SRCH-004-typed-public-browse-filters.md`.

After the marketplace fixture creates local demo sellers and active catalog
records, seed the private Home Goods examples with:

```bash
make seed-demo-home-goods-drafts
```

The command is DEBUG-only and idempotently creates one private Home & Garden
draft and one private Appliances draft. It neither publishes nor modifies an
existing draft.

The local billing adapter is DEBUG-only and never contacts Stripe. Sellers first
submit to staff moderation; a moderator may publish without payment or approve
and send a local payment link. The server-owned demo amount is $10 for the
primary county plus $5 per additional county across listing types. Use the
staff-only `/staff/billing/reconciliation/` screen to record the deterministic
payment; browser result pages never mark paid.

Generic listing county selection needs an operator-provided local ZIP-to-county
crosswalk after geography is loaded. The importer accepts only the HUD CSV
`ZIP,COUNTY` schema (including its documented ratio columns) or the
tab-delimited Harvard Dataverse `one2few_summy` schema. It verifies the
supplied checksum, performs no download or runtime lookup, and records
`--source-name` and `--source-url` exactly as supplied.

```bash
make import-hud-zip-counties \
  SOURCE=/path/ZIP_COUNTY.csv \
  SHA256=<sha256> \
  RELEASE_DATE=YYYY-MM-DD \
  RELEASE_VERSION=<release> \
  EXTRA_ARGS='--source-name "HUD USPS ZIP-County Crosswalk" --source-url "https://www.huduser.gov/portal/datasets/usps_crosswalk.html"'
```

For the public Harvard Dataverse DOI `10.7910/DVN/0U2TCB` release published
2024-08-12, use its tab-delimited `one2few_summy` file and its supplied
metadata. It is a HUD-derived ZIP-county crosswalk covering 2010–2023 and is
licensed CC BY-SA 4.0:

```bash
make import-hud-zip-counties \
  SOURCE=/path/one2few_summy.tsv \
  SHA256=<file-sha256> \
  RELEASE_DATE=2024-08-12 \
  RELEASE_VERSION=2024-08-12 \
  EXTRA_ARGS='--source-name "Harvard Dataverse one2few_summy" --source-url "https://doi.org/10.7910/DVN/0U2TCB"'
make seed-generic-demo-pricing
```

Well-formed county FIPS absent from the currently imported Census geography are
skipped, with the skipped-row count printed as a warning and in the final
summary. Malformed ZIP/FIPS, schema, and checksum failures remain fatal. The
command fails without writes if the source has no rows compatible with local
county geography.

The DEBUG-only pricing seed creates a $10 primary-county and $5 additional-
county quote configuration. Quotes are informative local demo records only;
generic submission continues directly to staff moderation without payment.

On the generic listing form, selecting an active state always reveals that
state's active counties, including when no crosswalk has been imported. A
five-digit ZIP is still required before save: the form labels crosswalk-verified
counties after it is entered, preserves any mismatched selection with clear
feedback, and server-side validation rejects a primary or additional county
that is not an imported candidate for the ZIP and state. Fixed and negotiable
asking prices are entered as USD dollars and cents; the application stores the
corresponding integer minor units.

`make seed-demo-generic-taxonomy` is the focused DEBUG-only, idempotent command
for public generic taxonomy/fact evidence. After active local reference data and
the marketplace catalog are present, it creates six synthetic, published
generic fixtures (Services, Business & Industrial, Jobs, Collectibles & Art,
Electronics, and Others) in at most one enabled county by default. Pass
`EXTRA_ARGS="--limit-counties N"` to the direct command when needed. Each
fixture has a primary leaf, seller tag, and safe additional fact; all except
Others also have a same-vertical controlled tag. Others stores its hidden
`General` primary leaf and requires a seller tag for public classification after
approval. The command uses the existing demo approval service and adds only its
synthetic local ZIP-to-county candidate. Its seller tags are public search terms
after approval; additional-fact values are not searchable. Others does not bypass
prohibited-content rules or moderation.

`make seed-demo-full` first runs `seed-demo-minimal`, then adds the versioned
marketplace catalog, public generic taxonomy/fact fixtures, bounded private
properties, rural, Home & Garden, and Appliances draft fixtures, plus draft
policy documents. It has the same database/DEBUG prerequisites and does not run
nationwide inventory: that seed requires an operator-provided Census import and
remains intentionally separate. Draft policy documents remain drafts; this
target does not activate policy.

## Local staff management console

Create the DEBUG-only local superuser and then visit `/manage/login/`:

```bash
make seed-demo-staff
```

The command is idempotent and never prints the password. It writes the local
credential to ignored `tmp/test-accounts.txt`. If `admin@local.test` already
exists, the command intentionally leaves its password and privileges unchanged.
The console dashboard is read-only and links to existing permission-protected
moderation, billing, policy, catalog, geography, and outbox workflows.
The seeded superuser can review listings at `/staff/moderation/`; a non-superuser
must be assigned the DEBUG-only `moderator` group (after
`make provision-staff-groups`). `is_staff` alone does not authorize moderation.
The same superuser can triage listing reports at `/staff/reports/`. The
`moderator` group includes the separate `reports.triage_listingreport`
permission; `is_staff` alone does not authorize report review. To try the
workflow, open a currently public listing's **Report this listing** link,
submit the CSRF-protected form, then sign in at `/manage/login/` and open
**Listing reports**. The local demo uses the existing superuser and does not
create additional privileged accounts for reports.

## Staff role groups

With `DEBUG=True` after migrations, run `make provision-staff-groups` to
reconcile the documented `moderator`, `support`, `finance`, and `operations`
groups. The command is idempotent and does not assign groups or staff access to
any user.

## Docker Desktop on WSL

When Docker Desktop is available only through the Windows CLI, project Make
targets automatically use `docker.exe`; otherwise they use the normal `docker`
command. Override `DOCKER` only when a different local Docker executable is
required.

## Local dependencies

- PostgreSQL in Docker Compose.
- Django console email backend for the local outbox workflow.
- Local filesystem media for DEBUG/test workflows.
- Local deterministic billing adapter; no Stripe credential, API call, or
  webhook is configured.
- No phone-verification provider is implemented.
- Public listing detail contains a lazy Google Maps iframe. It makes a
  third-party request to Google only when the frame loads; no local Google
  credential or API key is required. Local settings do not configure a CSP.
  Before a production restrictive CSP is enabled, allow
  `frame-src https://www.google.com` while the map frame remains enabled.

## Environment rules

- `.env` is local and ignored.
- `.env.example` contains names and safe examples, never secrets.
- settings fail fast for missing production values.
- environment parsing is centralized and typed.
- test settings avoid network calls.
- production-only security settings are not weakened globally for local convenience.

## Make targets

Recommended:

```text
make bootstrap          install/sync dependencies and initial setup
make run                local Django server
make compose-up         start PostgreSQL
make compose-down       stop supporting services
make test               full test suite
make test-fast          focused suite without coverage
make install-browsers   install Chromium for local browser tests
make test-e2e           run Playwright browser tests
make lint               Ruff check
make format             Ruff format
make typecheck          mypy
make check              all static and Django checks
make migration-check    makemigrations --check --dry-run
make migrate
make shell
make seed-demo-minimal
make seed-demo-full
make seed-demo-generic-taxonomy
make seed-demo-wanted-listings
make seed-demo-marketplace
make seed-nationwide-demo-inventory
make seed-demo-properties
make seed-demo-rural-drafts
make seed-demo-home-goods-drafts
make seed-demo-billing
make seed-demo-staff
make seed-draft-policy-documents
make launch-smoke
make cleanup-listing-media
make replay-payment-events
make expire-listings
make schedule-listing-reminders
make process-outbox
make inspect-outbox
make rebuild-listing-search-documents
make shell
```

After migrations are current, run `make seed-marketplace-catalog` to refresh
the LST-010 category posting profiles. The DEBUG-only command is idempotent;
it activates generic leaf profiles and keeps typed-leaf profile rows inactive
so the unified Create Listing flow uses existing typed fields for those leaves.

The unified Create Listing page keeps one primary controlled leaf category for
workflow selection and canonical URLs. It also offers same-vertical controlled
subcategory checkboxes, up to ten seller tags, and up to eight additional
label/value facts. These values are private while a listing is draft or in review;
approval makes tags searchable and renders facts only in the public Additional
details section. The catalog seed remains idempotent and does not create seller tags
or facts.

Every existing seller listing opens through the unified private owner detail and
can be edited at `/dashboard/listings/<uuid>/edit/`. The edit route retains the
persisted category/workflow and actual typed or generic detail representation,
then allows only `draft`, `changes_requested`, or `published` owners to save.
Published material edits immediately return to moderation; the owner view labels
controlled secondary tags, seller tags, custom facts, category-profile values, and
broker attribution consistently as private/pending until publication. On Create
Listing, **Show fields** and automatic JavaScript category selection preserve
workflow-eligible entered values without saving a draft; no-JavaScript follows the
same server flow. Legacy typed edit routes remain available for local compatibility
testing, but dashboard and owner/public edit links use the unified routes.

## Seed users

Provide a documented development command that creates deterministic local-only users:

- marketplace admin
- moderator
- verified seller
- unverified seller
- buyer

Never run this command in production unless it refuses safely.

## Browser tests

The foundation uses `pytest-playwright` for a compact set of end-to-end smoke
tests. Install the local Chromium runtime once with `make install-browsers`,
then run `make test-e2e`. Browser tests use Django's local test server and the
SQLite test database; CI runs model and migration checks against PostgreSQL
separately. The E2E target scopes Django's async-safety compatibility override
to the Playwright process only; application settings do not enable it.

Mobile browser coverage uses a 390px viewport. It verifies the progressively
enhanced Menu disclosure (including Escape), the no-JavaScript navigation
baseline, authenticated Create listing visibility, and absence of horizontal
document overflow on the public browse/nearby controls and generic listing
form. No special local server, browser flag, or front-end build step is needed.

## Local provider fakes

Provider interfaces should have explicit fakes:

- phone verification accepts a documented local code and records attempts
- email uses local SMTP capture
- media may use local storage while preserving upload/finalization service boundaries
- local billing uses a DEBUG-only, staff-only deterministic event through the
  replayable payment handler; Stripe integration remains intentionally absent

## Outbox and listing lifecycle operations

The local email backend writes notifications to the Django console; no AWS or
SES credentials are needed. These commands are deliberately explicit, so seed
commands cannot accidentally deliver email:

```bash
make schedule-listing-reminders
make expire-listings
make process-outbox
make inspect-outbox
make inspect-outbox EXTRA_ARGS="--replay <failed-event-uuid>"
```

`process-outbox` accepts `EXTRA_ARGS="--batch-size 25 --batches 4"`. It
reclaims leases older than `OUTBOX_LEASE_SECONDS` (default 300) and retries
delivery failures up to `OUTBOX_MAX_ATTEMPTS` (default 5). Production uses
Django SMTP only when the explicit SES settings are present; provisioning SES,
EventBridge schedules, bounce handling, and alarms are intentionally not part
of this local slice.

## Database resets

Document a safe local reset command. Never create a script whose default can target a non-local database. Require explicit environment checks and confirmation for destructive commands.
