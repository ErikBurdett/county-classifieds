# ADR-0018: Automatic refunds for rejected paid listings

**Status:** Accepted  
**Date:** 2026-07-23  
**Supersedes:** DEC-004 manual-review default

## Decision

When a staff moderator rejects a paid listing, create a full refund through the
payment adapter as part of the durable moderation transaction. The provider
event identity is deterministic per order so repeated or delayed moderation and
refund processing cannot issue a second refund. Browser routes never create
refunds.

The implemented `local_demo` adapter transitions paid orders to refunded and
records a provider-neutral `charge.refunded` event. A future Stripe adapter
must implement the same contract with verified provider events and operational
reconciliation.

## Consequences

This does not authorize Stripe credentials, real money movement, or a
production launch. Failed/mismatched events remain durable and replayable for
staff investigation.
