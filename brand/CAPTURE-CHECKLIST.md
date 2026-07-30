# Brand Capture Checklist

## Access and authorization

- [ ] Confirm the canonical production/staging URL.
- [ ] Confirm the developer is authorized to inspect and reuse assets/styles.
- [ ] Obtain original logo files and usage guidance.
- [ ] Record font names, source/license, available weights, and fallbacks.

## Reference screenshots

Capture full-page and cropped references at approximately 390px, 768px, and 1440px widths:

- [ ] masthead/logo
- [ ] desktop navigation
- [ ] mobile navigation
- [ ] headline/title stack
- [ ] article/list cards
- [ ] buttons and links
- [ ] forms/errors/help text
- [ ] promotional/ad treatments relevant to Market
- [ ] footer/legal/navigation
- [ ] any existing account/user interface

Name files with date, page, viewport, and state. Example:

```text
2026-07-22-home-390-mobile-menu-open.png
```

## Computed values

- [ ] body/background/text/link colors
- [ ] heading and body font family/weight/size/line-height/letter-spacing
- [ ] content/container widths and gutters
- [ ] spacing rhythm between sections/components
- [ ] borders, radii, shadows, dividers
- [ ] focus/hover/active/disabled/error/success states
- [ ] breakpoints and navigation transformations
- [ ] image ratios and crop behavior

## Approval

- [ ] Populate `brand-reference-manifest.json`.
- [ ] Mark each reference approved or rejected.
- [ ] Record any required marketplace divergence.
- [ ] Translate approved evidence to semantic tokens.
- [ ] Run `/brand-parity-review` on the first shared shell and listing card.
