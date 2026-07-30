# ADR 0012: Public Nationwide Directory Policy

**Status:** Accepted  
**Date:** 2026-07-23  
**Decision owners:** Project owner  
**Supersedes:** the public-route activation policy in ADR-0010 and LOC-001–003  
**Superseded by:** none

## Context

The initial geography rollout separated active reference records from
network-enabled inventory and made both controls prerequisites for public route
resolution. That made valid Census markets unvisitable when they had no
inventory or had not yet been promoted.

## Decision

All active Census state and county records are public directory records.
`is_active` is the sole public route and location-finder eligibility control.
Empty directory pages are intentional. `is_network_enabled` remains a separate
staff-owned inventory eligibility control and remains required by the public
listing selector.

New Census imports default newly created states and counties to active and
network-enabled. Reimports preserve existing flags. Operators can explicitly
enable all imported records with `enable_nationwide_directory`.

## Consequences

- State and county route resolvers and directory search filter only by active
  status (and parent-state activity for counties).
- Public listing visibility remains published plus active/network-enabled
  state and county checks.
- A staff member can hide a location directory page by making it inactive,
  without changing the durable Census reference record.
- The prior ADR and LOC feature specification are superseded only where they
  required network-enabled public route resolution.

## Validation

Tests cover active-only routes and finder results, network-disabled but active
directory pages, importer defaults, and the nationwide enable command.
