# Brand and UI System

## Current status

The public `thecountypost.com` domain was not resolvable from the research
environment on July 22, 2026. A user-directed local first-party stylesheet is
recorded in `brand/brand-reference-manifest.json` and verifies the color,
typography, shadow, and container tokens currently used by the marketplace.
Logo, icon, photography, spacing, radius, breakpoint, and motion values remain
unverified and must not be inferred.

Before visual sign-off, obtain one or more of:

- access to the live site from the development environment
- desktop and mobile screenshots of representative pages
- logo assets in SVG/PNG and usage rules
- the existing site stylesheet or design-system export
- computed styles for header, navigation, headings, body, links, buttons, cards, forms, borders, and footer
- font family names, font files/licensing source, and fallback stack

Record evidence in `brand/brand-reference-manifest.json`.

### M10 evidence boundary

The repository now contains a user-directed local first-party reference manifest
dated 2026-07-23. M10 consumes its existing color, typography, shadow, and
container tokens only. No logo, icon, photography, spacing, radius, breakpoint,
or motion value was inferred where the manifest has no verified value.

M10 has implemented shared navigation/footer, responsive controls, visible
focus, reduced-motion behavior, and semantic status treatment using those
available tokens. This is an implementation foundation, not brand-parity
approval: manual screen-reader review, complete first-party evidence, and
production performance/crawl evidence remain outstanding.

The local-demo UX hardening slice adds a native disclosed state directory,
multi-vertical public copy, readable browse cards and result context, contained
detail galleries with an explicit no-image state, and scannable seller creation
choices. These changes reuse existing tokens and introduce no brand assets or
new visual primitive values.

The responsive-navigation refinement keeps that boundary: the narrow masthead
uses the verified token system for its existing primary action and Menu
disclosure, while the desktop navigation remains inline. It does not claim
unverified breakpoint, icon, spacing, or motion values as CountyPost brand
evidence. The disclosure has a visible text label in addition to its menu
glyph, strong focus treatment, 44px minimum controls, and reduced-motion-safe
CSS. With scripting unavailable, its links remain visible rather than hidden.

## Design-token contract

All templates/components consume semantic custom properties, never scattered literal brand values.

Suggested layers:

```css
:root {
  /* Primitive values populated from verified brand evidence. */
  --brand-color-ink: ...;
  --brand-color-paper: ...;
  --brand-color-primary: ...;
  --brand-color-accent: ...;
  --brand-font-display: ...;
  --brand-font-body: ...;

  /* Semantic application tokens. */
  --color-text: var(--brand-color-ink);
  --color-surface: var(--brand-color-paper);
  --color-action: var(--brand-color-primary);
  --font-heading: var(--brand-font-display);
  --font-body: var(--brand-font-body);
}
```

Maintain tokens for:

- colors and states
- type scale and line heights
- spacing scale
- container widths
- borders and radii
- shadows
- focus ring
- transitions/motion
- image aspect ratios
- breakpoints
- z-index layers

## Visual relationship to CountyPost

The marketplace should feel like a product of the same publisher while remaining a distinct task-oriented application.

Match:

- masthead/logo treatment
- primary color and typography
- navigation rhythm
- headline hierarchy
- link/button language
- footer and legal patterns
- photography/crop character

Marketplace-specific additions:

- persistent state/county scope control
- prominent “Post a listing” action
- structured filter controls
- price and location hierarchy
- trust/moderation indicators
- featured placement labeling
- seller dashboard and progress states

## Component inventory

Build and document components before duplicating markup:

- site masthead and marketplace sub-brand
- state/county scope toggle
- search form
- primary/secondary/destructive buttons
- category/vertical tile
- listing card and featured listing card
- price, location, metadata, status badges
- filter panel and active-filter chips
- pagination
- image gallery
- seller summary/trust panel
- structured detail definition list
- form field, help, error, and required indicator
- multi-step listing progress
- upload picker and image reorder control
- moderation notice/change-request panel
- empty/error/loading states
- alert/banner/toast where necessary
- footer

Use Django template components/includes with clear context contracts. Do not introduce a JavaScript component framework solely for reuse.

## Accessibility

Minimum expectations:

- keyboard-complete navigation and form flows
- visible focus style using a token with sufficient contrast
- semantic headings and landmarks
- labels, descriptions, errors, and grouped controls
- no color-only state communication
- touch targets appropriate for mobile
- reduced-motion support
- image alt-text policy; decorative images use empty alt text
- meaningful button/link names
- accessible validation summary on multi-step forms
- contrast verified after real brand tokens are populated

Target WCAG 2.2 AA for public and staff workflows.

## Responsive behavior

Design mobile-first. Validate at representative narrow, medium, and wide viewports rather than targeting device names.

- cards retain readable price/title/location hierarchy
- filters become a clear disclosure/drawer without hiding active state
- scope toggle remains discoverable
- upload/reorder works without drag-only interaction
- tables in staff views have responsive alternatives
- listing detail prioritizes title, price, location, primary photo, and action intent

## Brand-parity workflow

Invoke `/brand-parity-review` after adding reference evidence or completing a UI slice. The review must compare:

- typography
- color
- spacing
- border/radius/shadow language
- header/footer relationship
- content density
- mobile behavior
- accessibility

The review outputs an evidence table: reference, implementation, difference, severity, and proposed token/component change.
