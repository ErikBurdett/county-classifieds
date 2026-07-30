# TheCountyPost Brand Reference Workspace

The marketplace must match TheCountyPost, but this kit deliberately contains no invented color, font, logo, or spacing values. Populate this directory from verified first-party evidence before visual sign-off.

## Preferred evidence, in order

1. Existing TheCountyPost design tokens or stylesheet source
2. Original logo assets and brand guide
3. Access to the live production/staging site
4. Desktop/mobile screenshots plus computed styles
5. Stakeholder-approved design samples

Do not use a search-result thumbnail, cached third-party screenshot, or AI-generated logo as brand truth.

## Capture workflow

1. Save approved logos under `brand/assets/` without changing originals.
2. Capture representative pages at mobile and desktop widths:
   - homepage/header/navigation
   - article/list page
   - form or newsletter component, if available
   - footer/legal area
3. Record each item in `brand-reference-manifest.json` with date, source, owner, and approval state.
4. Run `capture-computed-styles.js` from DevTools on the authorized live site after adapting its selector map.
5. Translate verified primitive values into semantic tokens based on `design-tokens.example.css`.
6. Store marketplace tokens in the application under `src/static/css/tokens.css`.
7. Invoke `/brand-parity-review` for each major UI slice.

## Rules

- Preserve licensing/source information for fonts and imagery.
- Do not commit restricted font binaries or proprietary source files unless the repository is authorized to hold them.
- Use semantic roles such as `--color-action` rather than component-specific raw values.
- Changing a primitive token should update the marketplace consistently without template edits.
- Accessibility contrast may require a marketplace-specific semantic token even when a source color is retained elsewhere; document any divergence.
