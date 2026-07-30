# ADR 0004: Use PostgreSQL 18

- Status: Accepted
- Date: 2026-07-22

## Context

The product needs relational integrity, transactions, typed vertical filters, full-text search, trigram matching, JSONB for limited metadata, and operationally managed backups. Amazon RDS supports PostgreSQL 18, whose support horizon is appropriate for a new application.

## Decision

Use PostgreSQL 18 for local development and RDS production, on the current approved minor version. Use psycopg 3. PostgreSQL full-text/trigram search is the Phase 1 search engine.

## Consequences

- One database supports business data and initial search.
- Search/index design must be measured with representative data.
- No OpenSearch cluster in MVP.
- Major/minor upgrade policy is part of operations.
