# Reference Data and Inventory Seeding

## Reference data

Reference data is versioned and imported through idempotent management commands.

### State/county data

The import source manifest records:

- source/provider
- source version/date
- checksum
- transformation code version
- imported counts
- changes/deactivations

Do not silently delete counties referenced by listings. Separate geographic existence from CountyPost network participation.

The U.S. Census 2025 National Counties Gazetteer is supplied by an operator as a
local ZIP file; it is neither downloaded by the application nor committed to
the repository. Verify the vendor checksum out of band, then validate the
artifact without writing data:

```bash
make import-census-geography \
  SOURCE=/secure/path/2025_Gaz_counties_national.zip \
  SHA256=<64-character-vendor-sha256> \
  RELEASE_DATE=YYYY-MM-DD \
  EXTRA_ARGS=--dry-run
```

The equivalent direct command is:

```bash
uv run python src/manage.py import_census_geography \
  /secure/path/2025_Gaz_counties_national.zip \
  --expected-sha256 <64-character-vendor-sha256> \
  --release-date YYYY-MM-DD \
  --dry-run
```

Omit `--dry-run` to apply the idempotent upsert. Each successful non-dry-run
creates an immutable `ReferenceImport` provenance record with source/version,
checksum, transformation version, and created/updated/unchanged counts. Newly
imported locations default to active and network-enabled; reimports preserve
existing staff activation flags and do not delete or deactivate records.

The recorded local import of the 2025 source loaded 52 state-equivalents and
3,222 counties. This establishes nationwide reference availability; it does not
by itself establish launch markets, production inventory, legal approval, or a
deployed public service.

To explicitly restore every imported location to those nationwide defaults, run:

```bash
make enable-nationwide-directory
```

The command reports its actual state and county update counts.

### Categories and verticals

`make seed-marketplace-catalog` runs the DEBUG-only,
idempotent `seed_marketplace_catalog` command. It applies catalog version
`2026.07.30.1` from `apps.catalog.marketplace_catalog` and reports exact
created, updated, and unchanged vertical/category counts.

The declarative definition owns only records identified by its exact vertical
slug and `(vertical slug, category slug)` pair. Re-runs restore the documented
name, parent, display order, and active state for those seed-owned identifiers;
they do not delete anything or alter staff-created records with other
identifiers. Autos keeps the established `autos` vertical slug and `cars`,
`trucks`, `suvs`, `vans`, `motorcycles`, and `other-autos` category slugs.

LST-010 profile v2 upserts stable supplemental-field definitions for every
generic active leaf. Typed leaves resolve to their existing detail forms and
their historical profile rows are made inactive, so they never receive generic
JSON fields. The current declarative coverage is 103 active generic profiles
with 671 controlled field definitions and 69 inactive typed-profile rows.
The local 2026-07-29 rerun retained 17 historical active fields in addition to
those definitions, for 685 active field rows. Re-runs never delete unknown
historical profiles, fields, or stored
attribute values; they restore only seed-owned identifiers. Run it after
applying `catalog.0008` and `listings.0015`.

This is browse/reference data, not seller eligibility. `Others` is a narrow
overflow taxonomy with a hidden internal `General` leaf; it requires a seller tag
for public classification after approval and does not bypass prohibited-content or
moderation policy. Autos has its approved
ListingKind/products and typed Automobile draft form. The eight typed
presentations—including Homes and Rentals—have local/demo public browse
exemplars, but Autos alone has a ListingKind/products and local billing
configuration. The command deliberately creates no `ListingKind`, product,
price-mode, or price records; pricing and policy for every other vertical remain
unresolved. Pets under Livestock & Animals are catalog vocabulary only and do
not approve a pet policy.

Changes to slugs still require redirect/SEO review. Historical listings retain
understandable category snapshots or protected references.

### Products/pricing

Product definitions are effective-dated. Historical orders store line snapshots. Stripe environment mappings are configuration/reference records and validated during deployment.

### Moderation reasons

Seed controlled reason codes with stable codes. Copy changes are versioned; used codes are deactivated rather than deleted.

## Launch inventory

Inventory-seeding operations for Potter and Randall should use normal or explicitly audited staff posting flows, not direct database inserts. Seed listings must:

- have real owners or approved staff attribution
- satisfy field/photo requirements
- pass moderation
- use correct payment/waiver policy
- be clearly non-test production content
- expire normally

## Local browse fixture

`make seed-demo-minimal` is the recommended fresh local-database sequence
after `make compose-up` and `make migrate`. With `DEBUG=True`, it runs the
bounded Texas/Autos reference, marketplace inventory, moderation reasons,
local billing, role-group, and local-staff seeds in dependency order. It does
not import Census geography, enable nationwide directory records, create media,
call external services, or activate policy documents.

`make seed-demo-marketplace` is a development-only fixture, not launch
inventory. It explicitly enables only Texas/Potter, New Mexico/Bernalillo,
Colorado/Denver, and Oklahoma/Tulsa, then publishes deterministic Autos through
the controlled publication service. It never enables imported nationwide
reference data. Re-running it does not duplicate users or listings. Local
credentials are written only to ignored `tmp/test-accounts.txt` and are not
printed.

`make seed-demo-properties` is separate, DEBUG-only, and requires two
pre-existing local demo seller accounts plus active reference/catalog records.
It idempotently creates one private Home draft and one private Rental draft
without changing or publishing existing user drafts. It is intentionally not
nationwide inventory: property publication waits for M5 submission/moderation
and M7 public visibility/search policy.

`make seed-demo-rural-drafts` is also separate, DEBUG-only, and requires the
same bounded local seller accounts, an active state/county, and the existing
`farm-ranch` / `livestock-animals` catalog records. It idempotently creates one
private Agricultural Equipment draft, one private Livestock draft, and one
private Pasture draft. It does not create ListingKinds, products, prices,
media, submissions, or public inventory, and it never alters or publishes an
existing draft. This is not nationwide inventory; rural publication remains
blocked on M5 submission/moderation and M7 public visibility policy.

`make seed-demo-home-goods-drafts` is separate, DEBUG-only, and requires the
same bounded local seller accounts, an active state/county, and the existing
`home-garden` / `appliances` catalog records. It idempotently creates one
private Home & Garden draft and one private Appliances draft. It does not
create ListingKinds, products, prices, media, submissions, or public inventory,
and it never alters or publishes an existing draft.

`make seed-demo-generic-taxonomy` is a DEBUG-only, idempotent local fixture for
public catalog-profile evidence. It creates six published, generic listings in
the first active, network-enabled county by default (or `--limit-counties N`):
Services, Business & Industrial, Jobs, Collectibles & Art, Electronics, and
Others. Each has its primary leaf, one seller tag, and one safe additional fact;
all except Others also have a same-vertical controlled tag. Others uses its hidden
`General` primary leaf. It uses a stable local-only seller, creates only the
fixture's synthetic ZIP-to-county candidate when needed, and publishes through
the existing `publish_demo_listing` approval service. Re-runs do not update or
delete existing user/seller data; only an unpublished command-owned fixture is
approved. Pets and typed Home & Garden records are deliberately excluded.

`make seed-demo-full` appends the bounded marketplace catalog, these public
generic taxonomy/fact fixtures, private draft fixtures, and non-binding draft
policy placeholders after the minimal sequence. Nationwide synthetic inventory
is intentionally excluded because it requires an operator-supplied Census
import; draft policy documents remain unactivated.

`make seed-demo-wanted-listings` is DEBUG-only and idempotently publishes up to
three clearly synthetic In Search Of examples against existing local demo
sellers, enabled counties, and active postable target categories. It does not
create a seller identity, represent a real request, add media, or modify
existing rows. Each fixture uses Contact with offer and no expiry under DEC-115.

## Synthetic data

`make seed-nationwide-demo-inventory` runs the DEBUG-only,
idempotent `seed_nationwide_demo_inventory` command. It creates exactly one
safe, published exemplar for each implemented typed presentation (Autos,
Homes, Rentals, Agricultural Equipment, Livestock, Pasture, Home & Garden,
and Appliances) in every active, network-enabled county. It uses four stable
local demo seller accounts, creates no media or exact property addresses, and
does not seed catalog-only verticals. The command approves each newly created
draft through the explicit `publish_demo_listing` system-approval service,
which records a durable `DIRECT_APPROVAL` moderation action. For a quick local
smoke test, pass `--limit-counties N`; normal invocation processes all enabled
counties in bounded database iterator batches and prints created, updated, and
unchanged counts.

The recorded full local run created 25,776 listings (eight exemplars in each of
3,222 active, network-enabled counties). These synthetic rows are local demo
data only, not production or launch inventory.

Load/performance test data belongs only in isolated environments. A generator should:

- create representative vertical distributions
- vary states/counties/prices/dates/statuses
- generate safe placeholder images
- avoid real personal data
- be reproducible from a seed
- support cleanup by batch ID

## Backfills

Data backfills are restartable, bounded, observable, and separate from schema migrations when they may be large. Record counts, errors, and completion markers.
