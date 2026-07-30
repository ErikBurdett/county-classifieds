# Cursor Skills and Rules Catalog

## How the configuration is divided

- `.cursor/rules/*.mdc` contains short constraints that attach automatically or remain always active.
- `.cursor/skills/<name>/SKILL.md` contains procedural workflows invoked from the slash menu.
- `docs/`, `templates/`, and accepted feature specs contain the detailed source of truth.

This avoids placing the entire architecture and roadmap in every Agent request.

## Manual Agent Skills

| Slash command | Use it for | Primary output | Edits code? |
|---|---|---|---|
| `/bootstrap-django-marketplace` | Create the initial Django foundation | Runnable project, quality gate, initial migration | Yes |
| `/resolve-product-decision` | Turn an unresolved policy/product issue into an explicit decision | Options, recommendation, ADR/register update | Documentation only |
| `/plan-marketplace-feature` | Convert a milestone/ticket into an implementation-ready specification | Feature spec and slices | Documentation only |
| `/implement-django-feature` | Implement one accepted spec or slice | Production code, tests, docs | Yes |
| `/design-domain-model` | Design models, invariants, constraints, indexes, and migration sequence | Domain design/ADR recommendation | Normally no |
| `/create-safe-django-migration` | Generate and review a PostgreSQL-safe migration | Migration, SQL/lock/deploy analysis | Yes |
| `/build-listing-vertical` | Add one typed vertical end-to-end | Detail model, forms, filters, admin, tests | Yes |
| `/build-moderation-workflow` | Add or extend moderator operations safely | Queue/actions/audit/notifications/tests | Yes |
| `/integrate-stripe-listing-payment` | Implement listing fee/upgrade Checkout and webhooks | Orders, idempotent handlers, reconciliation | Yes |
| `/brand-parity-review` | Compare UI against verified TheCountyPost evidence | Evidence/difference table and token fixes | Review; edits when requested |
| `/security-review` | Perform a threat-driven feature/diff review | Prioritized findings and regression tests | Review; edits when requested |
| `/test-marketplace-feature` | Build and execute a risk-based test matrix | Tests and acceptance coverage map | Yes |
| `/review-diff` | Senior review of the current branch | Findings, gaps, merge recommendation | No by default |
| `/prepare-aws-deployment` | Design/implement one AWS environment or deployment slice | IaC/config/runbook/deploy evidence | Yes |
| `/release-readiness` | Run a milestone/production go/no-go gate | Completed release review | Documentation/checks |
| `/debug-production-incident` | Investigate and mitigate a production-like incident | Timeline, mitigation, incident record | Only scoped fixes |

Most include `disable-model-invocation: true`, so they remain manual and do not add their descriptions to routine Agent context. Type `/` in Cursor chat to discover them.

## Project Rules

| Rule | Scope | Core purpose |
|---|---|---|
| `00-project-constitution` | Always | Product boundary, architecture, scope and change discipline |
| `10-django-python` | Python/project config | Django layering, typing, transactions, safe logging |
| `20-domain-model` | Models/services/selectors | Typed listing data, lifecycle, public visibility, privacy |
| `30-frontend-brand-accessibility` | Templates/static/brand | Server rendering, tokens, XSS safety, accessibility |
| `40-security-privacy` | Sensitive apps/settings | Authorization, uploads, secrets, abuse and privacy |
| `50-testing-quality` | Tests/CI | Risk-based coverage, retries, external-service fakes |
| `60-database-migrations` | Models/migrations | Expand/migrate/contract and PostgreSQL lock safety |
| `70-stripe-payments` | Billing | Server-owned pricing, webhook truth, idempotency |
| `80-aws-operations` | Docker/IaC/production | Stateless containers, ECS/RDS, health and observability |
| `90-documentation-decisions` | Docs/templates | ADR/spec traceability and honest completion evidence |

## Creating another skill or rule

Start from:

- `templates/CURSOR-SKILL-TEMPLATE.md`
- `templates/CURSOR-RULE-TEMPLATE.mdc`

A good skill is a repeatable procedure with an input, evidence-gathering phase, guardrails, verification, and an output contract. A good rule is short, scoped, actionable, and testable.
