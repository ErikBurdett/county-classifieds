---
name: resolve-product-decision
description: Convert an unresolved marketplace product or policy question into an explicit, traceable decision before implementation.
argument-hint: "<decision title or OPEN-DECISIONS item>"
disable-model-invocation: true
---

# Resolve Product Decision

Use this workflow when a feature depends on policy, money, identity, moderation, privacy, retention, or user-visible behavior that has not been approved.

## Procedure

1. Read `docs/14-OPEN-DECISIONS.md`, `docs/00-PRODUCT-CHARTER.md`, relevant feature/roadmap docs, and existing ADRs.
2. Inspect existing code only to identify constraints; do not let current code silently decide product policy.
3. Restate the decision in plain language for a non-technical stakeholder.
4. Separate:
   - source requirement
   - engineering constraint
   - assumptions
   - unknowns
5. Present 2–4 viable options. For each, cover user impact, operational impact, security/privacy, implementation effort, reversibility, and launch risk.
6. Recommend one option with a concise rationale.
7. Ask focused questions only when stakeholder input is genuinely required. Do not ask implementation trivia.
8. When a choice is supplied, create an ADR from `templates/ADR-TEMPLATE.md` and update the open-decision register.
9. Record consequences, rejected alternatives, effective date, owner, and what must change in specs/tests/runbooks.

## Guardrails

- Do not implement the dependent feature in this workflow.
- Do not mark a decision accepted without explicit stakeholder approval or an already documented authority.
- Do not manufacture legal, refund, prohibited-item, retention, consent, or brand policy.
- If the decision remains unresolved, produce a decision packet that can be sent directly to the stakeholder.

## Output

- decision statement
- options table
- recommendation
- stakeholder question(s), if any
- ADR path/status
- documents/specs now blocked or unblocked
