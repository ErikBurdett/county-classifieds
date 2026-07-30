# LST-009 — Universal Generic Listings

**Status:** Superseded in part by LST-010  
**Authorization:** User-approved 2026-07-23  

## Behavior
Authenticated active sellers can create a bounded generic listing in every active catalog category, including Pets, Jobs, Services, and each vertical's Other category. LST-010 replaces the separate generic entry point with a unified category-resolved form and catalog-owned supplemental profiles. Generic rows use `GenericListingDetails`; they never create typed detail rows.

The form requires title, description, category, item price mode, city/state/ZIP, primary county, and permits a private street address. It exposes all active counties for a selected active state before ZIP confirmation; JavaScript-enhanced forms provide state-scoped, authenticated county searches while retaining the primary `county` select and `additional_counties` multi-select as the no-JavaScript fallbacks and submitted server-validated fields. “List on Nearby Counties” renders selected additional counties as removable tags, prevents duplicate or primary-county tags, and keeps the native multi-select synchronized. County search accepts at most 80 characters, returns at most 20 active same-state matches, and never returns listing or cross-state data. After a five-digit ZIP is entered, it labels the primary county and every selected tag with a text verified/not-verified status from the loaded offline crosswalk without discarding the seller's selected choices. When crosswalk data is absent, the form preserves selections and explains that verification cannot occur until it is imported. Server-side validation still requires the primary and every additional county to be an active candidate for that ZIP and state. The local-demo placement display updates as $10 primary plus $5 per selected additional county; it is not a payment claim, and the server quote/snapshot remains authoritative. Fixed and negotiable item prices are entered as USD dollars and cents and stored as integer minor units; free and contact-for-price listings cannot include an amount. Exact street address and ZIP are not public, mapped, indexed on public surfaces, or exposed in seller-independent selectors. Public copy says location is city/county/state and an address may be provided on request. Buyer messaging is not included.

## County distribution
`Listing.county` is the canonical primary scope. `ListingCountyPlacement` holds zero or more unique additional same-state counties. Every primary/additional choice must be an active candidate in the loaded offline ZIP-to-county reference data. Public browse can show the one listing in selected additional county scopes; detail routes there 301 to the primary county route. Publication still uses the central public visibility selector.

## ZIP reference data
`ZipCountyReference` imports a locally supplied ZIP-to-county crosswalk; runtime
performs no network request and does not infer missing mappings. The command
accepts only the HUD CSV `ZIP,COUNTY` schema (including documented ratio
columns) and the tab-delimited Harvard Dataverse `one2few_summy` schema. It
verifies SHA256, release date/version, operator-supplied source metadata, and
county FIPS; it is transactional/idempotent and supports `--dry-run`. A
syntactically valid source FIPS that is not present in local imported geography
is skipped and reported in the command summary; the import fails without writes
when no source rows match local counties.

Run `make import-hud-zip-counties SOURCE=/path/ZIP_COUNTY.csv
SHA256=<sha256> RELEASE_DATE=YYYY-MM-DD RELEASE_VERSION=<source-version>
EXTRA_ARGS='--source-name "<supplied source name>" --source-url "<supplied
source URL>"'`. No fixture is committed because no locally supplied file with
verifiable provenance was available. The public Harvard Dataverse release DOI
`10.7910/DVN/0U2TCB` (published 2024-08-12; HUD-derived 2010–2023; CC BY-SA
4.0) must be recorded as its own supplied source metadata, not as a HUD-primary
source. A ZIP/county candidate is a lookup reference, not postal delivery
verification.

## Local demo pricing and lifecycle
The item price mode is separate from placement fees. DEBUG-only `seed_generic_demo_pricing` configures server-owned $10.00 USD primary and $5.00 USD additional-county products. Submission snapshots an `Order`/`OrderLine` quote if configured but never grants payment state and does not block generic moderation. This is local-demo configuration, not production policy. Generic drafts proceed `draft → submitted → in_review → published` through existing moderation/audit; the Autos payment lifecycle is unchanged.

## Security, tests, rollout
All mutations require owner and active-account checks plus CSRF. Draft detail returns 404 to non-owners. Private address data is absent from public presenters, templates, maps, and sitemap-facing selectors. Apply migrations `locations.0004`, `catalog.0007`, and `listings.0013`; load geography before the crosswalk. Rollback removes routes/UI first; additive reference/detail/placement data remains for a forward fix.
