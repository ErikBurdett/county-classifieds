# ADR 0008: Marketplace Identity Boundary

- Status: Accepted
- Date: 2026-07-22

## Context

The source material does not state whether Marketplace accounts are separate from existing CountyPost accounts. Coupling to an unknown identity system would block progress and may compromise the desired deployment independence.

## Decision

Create a marketplace-owned custom Django user model and seller profile for launch. Keep authentication services and external identity identifiers compatible with a later OIDC/SSO integration. Do not share database tables with a news-site application.

## Consequences

- Fast, independent implementation and deployment.
- Users may initially have a separate Marketplace account.
- Future SSO requires account linking/migration and a new accepted ADR.
- This ADR must be accepted or replaced before M1 implementation.
