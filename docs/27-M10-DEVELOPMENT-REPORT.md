# M10 Development Report

## Delivered

- Refined unified listing create/edit into numbered essential sections with
  open native optional disclosures, compact controlled-tag choices, linked
  error summaries, and responsive 390px safeguards without changing listing
  field, taxonomy, broker, or moderation semantics.
- Added authenticated, active-only same-origin state/territory and state-scoped
  county candidates for progressive combobox enhancement. Native selects remain
  the no-JavaScript and submitted controls; selection never auto-submits.
- Added keyboard Arrow/Enter/Escape coverage for generic and typed location
  flows, including Alaska county-equivalent names and horizontal-overflow checks.
- Reused only token values recorded in `brand/brand-reference-manifest.json`;
  no assets or new brand values were introduced.
- Reinforced shared navigation, footer, touch targets, visible focus, responsive
  staff tables, status text, and reduced-motion behavior.
- Added public canonical/meta-description behavior, `robots.txt`, and bounded,
  streaming directory/listing sitemap endpoints.
- Added browser-facing semantics for dashboard and moderation actions, plus
  sitemap/canonical/robots behavior tests.
- Added a server-rendered mobile navigation baseline with a small deferred
  disclosure enhancement at `56rem`. The labeled Menu button reports state,
  Escape returns focus to it, normal navigation closes the disclosure, and
  active sellers retain a visible Create listing action.
- Refined narrow and tablet layouts for browse filters/cards/pagination, the
  nearby county rail, detail/map actions, seller and staff dashboards, generic
  county controls, messages, and footer. Browser checks at 390px cover
  semantic menu behavior and horizontal-overflow guards.
- Added a mobile browse-filter disclosure with an open no-JavaScript baseline,
  `aria-expanded`, Escape/focus handling, and error-open behavior. Validated
  active-filter links, reset, clear-all, and pagination now omit arbitrary
  request keys while preserving remaining filter state and nearby distance.
- Grouped seller listing-row controls for narrow touch layouts and verified
  mobile seller/staff-management dashboard overflow and permitted operation
  links without changing actions, permissions, or lifecycle behavior.

## Security and operations

No migration, lifecycle, authorization, or privacy policy change. Listing
detail now contains a lazy Google Maps iframe, which makes a third-party
request to Google when its frame loads; it uses the privacy-safe presenter map
query, has `referrerpolicy="no-referrer"`, and does not use an API key or map
script. Sitemaps use the existing public-visibility selector and never disclose
private listing or account data. No production CSP is configured today; before
a restrictive CSP is activated, it must allow
`frame-src https://www.google.com` for the map frame or the frame must be
removed.

## Known limitations

Manual screen-reader review remains required for critical seller and moderator
flows. Production performance measurement and crawl telemetry are not available
in this environment; query budgets are verified by selector shape and tests,
not production measurements.

This responsive slice has no migration, route, authorization, listing,
moderation, pricing, search, map, SEO, or privacy-policy impact. It adds no
brand asset, framework, or third-party dependency and preserves normal
server-rendered navigation and form submissions when JavaScript is disabled.

## Verification

Verified locally on 2026-07-27: `make check` passed (214 non-browser tests, 5
PostgreSQL-only skips, 14 browser tests deselected, 85.37% coverage) and
`make test-e2e` passed (14 Chromium tests). No migration was generated.
