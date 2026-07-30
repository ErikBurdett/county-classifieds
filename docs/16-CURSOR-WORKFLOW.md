# Cursor Workflow

## Division of responsibility

Use three layers:

- **Project rules**: short, persistent constraints that should apply automatically to relevant files.
- **Agent skills**: procedural workflows invoked for a specific task.
- **Repository docs/specs**: detailed source of truth read only when relevant.

Do not duplicate entire architecture documents inside always-on rules. It wastes context and increases contradictions.

## Skill behavior

Skills live at:

```text
.cursor/skills/<skill-name>/SKILL.md
```

The folder name must match the `name` frontmatter. Most kit skills use:

```yaml
disable-model-invocation: true
```

This makes them manual slash workflows and limits routine context growth. If a project-level skill is not visible:

1. update Cursor
2. fully restart the application
3. confirm the repository root is open
4. verify folder name/frontmatter match
5. confirm imported-config settings are not interfering
6. temporarily remove `disable-model-invocation` to diagnose detection

Avoid installing large unrelated global skill collections.

## Standard feature loop

### 1. Plan

```text
/plan-marketplace-feature [feature/ticket]
```

The agent inspects docs and code, identifies decisions, produces a feature spec, and does not implement.

### 2. Implement

```text
/implement-django-feature [accepted feature spec path]
```

Require the agent to state planned files, migration impact, and tests before editing.

### 3. Test

```text
/test-marketplace-feature [feature or changed paths]
```

The skill builds a risk matrix, adds missing tests, and runs the smallest relevant set followed by the full gate.

### 4. Review

```text
/review-diff
```

Review correctness, authorization, transaction boundaries, migrations, queries, idempotency, privacy, accessibility, and scope.

### 5. Specialized reviews

Use as applicable:

```text
/security-review
/create-safe-django-migration
/integrate-stripe-listing-payment
/brand-parity-review
/prepare-aws-deployment
/release-readiness
```

## Prompt practices

Good prompt:

```text
/implement-django-feature docs/features/M5-C-request-changes.md
Limit the change to moderation and listing services/templates. Do not add messaging. Preserve existing public visibility selectors. Show the migration SQL before applying it.
```

Bad prompt:

```text
Build moderation and make it production ready.
```

## Context practices

- Reference exact docs/files with `@`.
- Start a fresh chat when moving to a different milestone or after context becomes large.
- Ask the agent to summarize accepted decisions into the feature spec before implementation.
- Keep generated plans committed so a new chat can resume without conversational memory.
- Exclude media, virtual environments, static build output, and large source documents with `.cursorignore`.

## Change-size practices

A single agent change should ideally have:

- one coherent outcome
- one primary domain owner
- a small migration or none
- tests in the same change
- no unrelated formatting/refactor sweep

Split model foundations, data backfills, behavior switches, and destructive cleanup into separate changes.

## Git practices

- Commit the clean baseline before agent edits.
- Review `git diff --stat` and full diff frequently.
- Never let an agent force-push or rewrite shared history.
- Use small branches/PRs.
- Do not combine dependency upgrades with product features.
- Keep migrations committed and ordered.

## Human review hot spots

Always read carefully:

- settings and middleware order
- custom user and auth changes
- model constraints and migrations
- permission checks
- `transaction.atomic`, locks, and retries
- Stripe/webhook code
- S3 upload authorization
- raw SQL
- admin actions
- user-content rendering
- logging of payloads/PII
- infrastructure IAM and network rules
