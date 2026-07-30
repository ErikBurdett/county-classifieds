---
name: brand-parity-review
description: Compare a marketplace UI slice with verified TheCountyPost brand evidence and produce or implement token/component corrections.
argument-hint: "<page/component or reference evidence>"
disable-model-invocation: true
---

# Brand Parity Review

Do not infer the brand from memory or invent missing values.

## Evidence gate

1. Read `docs/08-BRAND-UI-SYSTEM.md` and `brand/brand-reference-manifest.json`.
2. Confirm the reference assets/screenshots/styles exist and are authorized for project use.
3. If evidence is missing, produce a capture checklist and stop before asserting parity.

## Compare

At representative mobile, medium, and desktop widths, assess:

- masthead/sub-brand relationship
- logo usage and clear space
- font families, weights, scale, line height, and headline rhythm
- color roles and contrast
- spacing/container/grid rhythm
- border, radius, shadow, and divider language
- links, buttons, fields, cards, navigation, footer
- imagery ratios/crops
- content density and editorial tone
- focus, errors, keyboard flow, reduced motion, and other accessibility behavior

## Implementation rule

Correct semantic tokens and shared components first. Do not fix repeated mismatches with scattered one-off CSS. Preserve marketplace-specific usability such as the scope toggle, filters, trust states, and prominent posting action.

## Output

Create an evidence table with:

- reference artifact/location
- reference property/value
- implementation property/value
- difference
- severity
- token/component correction
- verification status

If asked to edit, implement only approved corrections and rerun visual/accessibility checks. Never claim pixel parity without actual comparison evidence.
