# ADV-001 — Static sponsored ads and partner directory

**Status:** Implemented locally  
**Authorization:** User-approved 2026-08-03

## Outcome

The marketplace mirrors the County Post's deployment-managed sponsor system:
inline creative slots on public market pages, a sitewide banner slot, and an
indexable `/partners/` directory. It is distinct from paid listing
`FeaturedPlacement`.

## Scope

- Keep the approved County Post `ad-assets` directory in this repository and
  register it as a prefixed Django static-files source.
- Keep the creative catalog in version-controlled Python, not a database or
  Django admin workflow.
- Render square inline and wide banner creative slots with progressive,
  reduced-motion-aware carousel controls.
- Render compact sponsor creatives beside the market finder and listing filters,
  choose a deterministic sponsor for each county hero, and insert a labeled
  creative after every third public listing card.
- Use clearly visible sponsored disclosures and a partner directory split
  between external/nationwide and county founding partners.

## Security and privacy

- External links use `target="_blank"` with
  `rel="noopener noreferrer sponsored"`.
- Catalog entries are deployment-reviewed constants. No public input, ad
  purchase flow, click tracking, impression tracking, or external asset fetch
  is introduced.
- Partner placeholders point internally to `/partners/`; their directory
  cards do not fabricate an external destination.

## Boundaries

- This is not `FeaturedPlacement` and does not resolve DEC-107.
- Production ad sales, self-service creative uploads, targeting, scheduling,
  billing, analytics, and legal-policy expansion are separate decisions.
- Static creatives are copied into this independently deployed marketplace;
  the app has no runtime dependency on the County Post project.

## Verification

Test static catalog ordering, partner deduplication and grouping, rendering,
link attributes, public placement, mobile layout, and asset paths. No migration
is expected.
