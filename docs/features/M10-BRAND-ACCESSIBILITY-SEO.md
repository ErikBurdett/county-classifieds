# M10: Brand parity, accessibility, and SEO

## Scope

M10 strengthens the existing server-rendered marketplace using the verified local
first-party token manifest. It covers shared navigation/footer, responsive
controls, public metadata/canonicals, crawler controls, and sitemap generation.
It does not change listings, moderation, payment, account permissions, or
visibility policy.

## Behavior and safety

- Active state/county routes and the location finder use `is_active` only, per
  ADR-0012; `is_network_enabled` remains the stricter public-inventory
  requirement. The current sitemap implementation intentionally requires both
  flags for state/county rows and uses `public_listings()` for listing rows.
  Drafts, staff/account/billing routes, non-public listings, and private media
  are never emitted.
- Sitemap rows are page-bounded at 1,000 URLs and stream XML. They query only
  route fields, avoiding per-row related-object queries.
- Clean active state/county routes remain indexable. Any browse query (filters,
  sorting, or pagination) is `noindex,follow` and canonicalizes to its route.
- Listing detail metadata contains only public listing, city, and state facts.
  No JSON-LD is emitted because the currently available facts cannot safely
  satisfy a product schema across every vertical without privacy leakage.
- Home, active state/county directory, market-finder, and public listing pages
  use the `locations` public-presentation layer for title, description,
  canonical, Open Graph, and Twitter-card metadata. Query variants retain their clean-route
  canonical in both canonical and `og:url`. Listing metadata never reads
  seller/contact data, private addresses, general-area text, coordinates, or
  listing description. An absolute `og:image` is emitted only for a ready,
  processed public listing rendition; there is no fabricated brand image or
  original-upload URL.
- County-route metadata uses the imported county-equivalent display name with
  its state and never appends a generic `County` suffix. This preserves names
  such as boroughs, census areas, parishes, and independent cities.
- Public listing cards and galleries use the processed image endpoint only.
  Known image dimensions are emitted as `width`/`height`; browse-card and
  below-fold gallery images use lazy loading and asynchronous decoding. Empty
  image states remain explicit and accessible.
- Listing detail embeds a lazy-loaded Google Maps iframe and retains external
  Google Maps search and directions links as fallbacks. The iframe has no API
  key or page-load JavaScript and uses `referrerpolicy="no-referrer"`; it makes
  a third-party Google request only when the lazy frame loads. The destination
  is city/county/state by default; only an explicitly public exact Home or
  Rental address may be included. Coordinates and general-area text are never
  used.
- No production CSP is configured today. Before a restrictive CSP is enabled,
  it must allow `frame-src https://www.google.com` for this embedded map (or
  the map must be removed); this change does not add a CSP.
- The market finder and public state/county listing filters progressively
  enhance their existing GET forms. A same-origin, bounded fragment response
  is requested only after finder text is nonblank or a browse control changes.
  JavaScript errors leave existing results intact, while ordinary GET submission
  and pagination remain the no-JavaScript fallback.
- County browse may additionally expose the DEC-114 local-demo nearby rail.
  Its labeled native 10–250 mile range control retains GET state; query URLs
  remain `noindex,follow` with route-only canonicals. The rail uses public
  Census county internal points only, is labeled approximate, and is omitted
  when the current county has no imported coordinates.

## Non-goals

No new logo/assets, analytics, map API integration, client framework, or
genuine user/listing radius-search policy change.

## Mobile navigation and responsive refinement slice

### Scope

- At viewport widths up to `56rem`, the shared masthead progressively enhances
  into a labeled Menu disclosure. It exposes `aria-expanded` and
  `aria-controls`, closes with Escape while returning focus to the trigger, and
  closes when a navigation control is activated. It does not trap focus.
- The server-rendered default keeps all primary-navigation links visible and
  usable when JavaScript is unavailable. Active authenticated sellers retain a
  separate, visible Create listing action at narrow widths.
- Public browse/filter/pagination cards, the nearby county rail, listing
  detail/map actions, seller dashboard, generic county controls/tags, staff
  dashboard, messages, and footer receive mobile and tablet layout safeguards.

### Non-goals and safety

This adds no route, API, migration, listing, moderation, permission, search,
SEO, map, or pricing behavior. It introduces one same-origin deferred static
script for navigation only; normal links, GET filters, and POST forms remain
their server-rendered behavior with JavaScript disabled. Existing tokens are
reused; no new brand asset, font, framework, or third-party dependency is
introduced.

### Acceptance coverage

Browser checks use a 390px viewport for menu toggle/Escape/no-JavaScript
baseline, authenticated Create listing availability, browse/filter/nearby
controls, and generic county form horizontal-overflow guards. They assert
roles, labels, disclosure state, and document width rather than visual pixels.

## Local-demo UX hardening slice

This focused template and CSS slice keeps the existing server-rendered,
no-JavaScript public and seller workflows while improving their local-demo
presentation:

- The home page describes the multi-vertical marketplace, leads with the
  existing market finder, and keeps every active state directly linked within a
  native, initially collapsed directory.
- State and county browse pages expose a context-preserving reset URL, an
  `aria-live` result summary, and clearer card/action focus and hover feedback.
- Public details use responsive contained-image gallery cells, an explicit
  no-image state, separated facts/description sections, and distinct save and
  report actions. Existing favorite and report permissions/privacy behavior is
  unchanged.
- The seller dashboard groups creation options and provides an actionable empty
  state. Shared navigation/footer gains current-page and landmark cues.

This does not add full-text search, geospatial/radius search, map embedding,
Google account integration, inventory, media, seller lifecycle, report, or
favorite policy. It reuses the existing bounded query/form parsing and public
visibility selector; it has no database or migration impact.

## Tests and rollback

Tests cover robots, sitemap directory eligibility, sitemap pagination endpoint,
browse canonical/noindex and Open Graph URL output, public metadata privacy,
processed-image eligibility/layout attributes, public map privacy/link safety,
live result updates, and no-JavaScript GET fallback. Roll back by reverting
M10 templates, styles, static enhancement script, presentation layer, and core
SEO routes; there is no data migration or persistent state.

## Seller create-form accessibility refinement

- The unified seller create/edit form keeps labeled native location selects and
  open optional sections for the no-JavaScript baseline. JavaScript adds
  authenticated same-origin state/territory and county comboboxes with
  listbox roles, Arrow/Enter/Escape operation, and synchronized selects.
- Error summaries link to invalid controls and receive focus after an invalid
  enhanced submission. Responsive form sections, result options, and chips
  use existing minimum target sizing and must not create horizontal overflow at
  390px.
- This is presentation/progressive enhancement only: it does not add a
  location provider, public endpoint, policy change, persistent state, or
  migration.

## Mobile browse and operations slice

### Scope

- At widths through `45rem`, the public browse filters progressively enhance
  into a labeled disclosure. The server-rendered baseline remains open and
  usable without JavaScript; enhanced filters begin closed only when no
  validated value or error is present. A populated or invalid form is open,
  reports `aria-expanded`, closes on Escape with focus returned to its trigger,
  and moves focus to the error summary after an invalid response.
- Browse pages render removable active-filter links from successfully validated
  `PublicBrowseForm` values only. Search, vertical, category, county, prices,
  Autos fields, non-default sort, and county nearby distance are represented
  where applicable. Removing a chip resets pagination and preserves remaining
  validated state; reset retains a selected nearby-distance context, while
  Clear all returns to the route.
- Seller row actions are grouped and stack at narrow widths. Management metrics
  and permitted workflow links use narrow responsive grids; staff permissions
  and all existing routes/actions remain server-authoritative.

### Non-goals and safety

This slice does not add a filter endpoint, client-side query authority,
migration, listing/lifecycle change, permission change, staff data, radius
search, canonical rule, or SEO policy. Query links and pagination are generated
from validated allowlisted fields, never arbitrary query-string keys. Live
result fragments and ordinary GET submissions retain their existing behavior.
