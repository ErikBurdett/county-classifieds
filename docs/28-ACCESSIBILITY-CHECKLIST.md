# M10 Manual Accessibility Checklist

Run on narrow, medium, and wide viewports before release.

- Navigate every public, account, draft, media, moderation, and billing page by
  keyboard only; confirm the skip link and every focus indicator are visible.
- Submit each primary form with invalid data; confirm the summary is announced,
  labels and help remain associated with fields, and errors are understandable
  without color.
- Use a screen reader to confirm page title, one `h1`, landmarks, table headers,
  listing-card links, status text, and moderation form labels.
- Check 200% browser zoom, reflow, mobile touch targets, horizontal staff-table
  access, and `prefers-reduced-motion`.
- Confirm public image alt text is useful and private staff/address/payment/VIN
  data is not present in public output.
