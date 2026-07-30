# ADR 0001: Use a Django Modular Monolith

- Status: Accepted
- Date: 2026-07-22

## Context

The marketplace has multiple domains—listings, vertical details, moderation, billing, media, notifications, and future messaging—but begins as one product, one team, one database, and one deployment boundary. Straightforward AWS deployment is a priority.

## Decision

Build one Django application and PostgreSQL database with explicit app/module boundaries. Use one container image for web, worker, and one-off commands. Do not create county, vertical, payment, search, or moderation microservices for MVP.

## Consequences

- Simple transactions across listing/payment/moderation state.
- One deployment and observability model.
- Domain boundaries must be enforced by code organization and review rather than network APIs.
- Future extraction requires services/selectors/events to remain explicit.
- A module may be extracted only after measured scaling, ownership, reliability, or release-independence needs justify it.
