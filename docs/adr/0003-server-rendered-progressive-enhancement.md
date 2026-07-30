# ADR 0003: Server-Rendered Django with Progressive Enhancement

- Status: Accepted
- Date: 2026-07-22

## Context

The marketplace is form-heavy, search/browse-oriented, SEO-relevant, and moderation-driven. Deployment simplicity and a single origin are priorities. A React SPA would add API, authentication, build, routing, error-state, and testing complexity without a demonstrated need.

## Decision

Use Django templates and semantic HTML as the baseline. Add small progressive enhancements for filters, uploads, and staff efficiency only when the non-JavaScript/server path remains coherent. Do not create a React SPA for Phase 1A.

## Consequences

- Faster first render, simple SEO, and simpler CSRF/auth behavior.
- UI state must be reflected in URLs/forms.
- Complex interaction may eventually justify isolated JavaScript components or a future API, requiring a new ADR.
