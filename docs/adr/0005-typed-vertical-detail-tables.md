# ADR 0005: Use Typed One-to-One Vertical Detail Tables

- Status: Accepted
- Date: 2026-07-22

## Context

Listings share common identity, location, price, publication, and seller fields, while each vertical needs distinct required fields and filters. An EAV model would weaken validation, constraints, query readability, indexing, and type safety.

## Decision

Use one common `Listing` table and one-to-one typed detail tables for each meaningful vertical/subtype. Store frequently filtered/sorted values in columns. Limit JSONB to secondary metadata that is not a core invariant or common filter.

## Consequences

- More explicit models/forms/migrations.
- Clear validation and performant indexes.
- Adding a vertical requires an intentional model/form/filter slice.
- Cross-vertical browse uses common fields; vertical browse joins the compatible details table.
