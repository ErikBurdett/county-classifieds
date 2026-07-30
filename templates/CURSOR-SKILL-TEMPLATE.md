---
name: replace-with-kebab-case-name
description: State exactly when Cursor should use this workflow and what outcome it produces.
argument-hint: "<required input>"
disable-model-invocation: true
---

# Skill Title

One-sentence purpose and whether the workflow plans, edits, reviews, or operates.

## Preconditions

- Required decision/spec/input
- Repository/environment state
- Required access or evidence

## Read first

- `docs/...`
- relevant ADRs/specs
- exact code/config paths discovered from the repository

## Procedure

1. Inspect before editing.
2. State scope, non-goals, risks, expected files, migrations, and tests.
3. Perform the smallest coherent task.
4. Verify with actual commands and user-visible/operational evidence.
5. Update the source-of-truth documentation.

## Guardrails

- Explicit prohibited shortcuts
- Security/data/authorization requirements
- Conditions that require stopping for a decision
- Scope that must not be pulled in

## Output

- files/behavior changed
- migrations and deployment impact
- commands/tests and actual results
- unresolved risks/decisions
- rollback or next slice

<!--
Best practices:
- Folder must match `name`: `.cursor/skills/<name>/SKILL.md`.
- Keep the description specific enough for discovery.
- Keep procedural detail here; keep universal constraints in project rules.
- Use `disable-model-invocation: true` for manual slash workflows that should not add routine context.
- Do not encode secrets, transient environment values, or undocumented policy.
-->
