# Validation Record

## Latest recorded application verification

**Public seller profiles, fulfillment availability, sold retention, and
advertising (2026-08-04):** applied `accounts.0004`/`0005` and
`listings.0021`/`0022` successfully to local PostgreSQL. `make check` passed:
Ruff formatting/linting, mypy (184 source files), Django and migration checks,
320 non-browser tests passed, 6 PostgreSQL-only tests skipped, 26 browser tests
deselected, and 85.36% coverage. `make test-e2e` passed: 26 Chromium tests.
The verification covers public-profile privacy, moderated revisions, seller-feed
sold retention, static sponsor placements, and responsive in-feed ads. It does
not represent production advertising, payment, profile-media, or provider
operations.

**Moderation/payment/image review/notifications (2026-08-03):** inspected the
additive `listings.0020` and `notifications.0001` migration SQL, then applied
both successfully to the local PostgreSQL database. `listings.0020` adds
per-image moderation data and explicitly backfills existing ready images as
approved; `notifications.0001` creates recipient/read-state indexes and a
unique event idempotency key. `make check` passed: formatting, lint, mypy (171
source files), Django and migration checks, 303 non-browser tests passed, 6
PostgreSQL-only tests skipped, 24 browser tests deselected, and 85.32% coverage.
`make test-e2e` passed: 24 Chromium tests, including mobile notification
navigation, the explicit no-payment moderation action, and no-horizontal-
overflow assertions. The local adapter is DEBUG-only; no Stripe SDK, webhook,
or production payment policy was introduced.

**LST-011 In Search Of/Wanted listings (2026-07-31):** inspected
`sqlmigrate listings 0019` (additive non-null `intent` with `offer` database
default, intent check constraint, and intentional public intent/state index),
then applied `listings.0019_listing_intent` successfully to the local database.
Focused wanted, unified-workflow, and search tests passed: 51 passed, 1
PostgreSQL-only test skipped. `make check` passed: Ruff formatting/lint, mypy
(158 source files), Django checks, migration check, 291 non-browser tests
passed, 6 PostgreSQL-only tests skipped, 23 browser tests deselected, and
85.00% coverage. The first `make test-e2e` run exposed four existing-browser
URL/heading assertions affected by the new default offer control; after
canonicalizing the default control in the live-search script and preserving the
standard heading, the rerun passed: 23 Chromium tests, 297 deselected. The
migration does no Python backfill: existing rows receive `offer` through the
database default. Public visibility remains centralized, Wanted is generic-only,
and DEC-115 records target-category media requirements with no expiry.

**Documentation reconciliation and pre-commit cleanup (2026-07-30):** ran
`uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src`,
`uv run python src/manage.py check`, and
`uv run python src/manage.py makemigrations --check --dry-run --settings=config.settings.test`;
all passed (156 source files checked by mypy, no Django issues, and no migration
changes). `uv run pytest -m "not e2e"` passed: 279 passed, 6 skipped, 23
deselected in 50.58s, with 85.15% coverage. `make test-e2e` passed: 23 Chromium
tests passed, 285 deselected in 26.12s. This docs-only cleanup introduced no
application behavior, migration, schema, seed, or security-boundary change.

**Others overflow vertical (2026-07-30):** confirmed `DEBUG=True`, then ran
`make seed-marketplace-catalog` and `make seed-demo-generic-taxonomy` locally.
The first run created 1 vertical, 1 category, 1 profile, and 1 Others fixture;
the second reported 19 unchanged verticals, 229 unchanged categories, 172
unchanged profiles, and 6 unchanged generic fixtures. `make check` passed:
Ruff formatting/lint, mypy (156 source files), Django checks, migration check
with no changes, 279 non-browser tests passed, 6 PostgreSQL-only tests skipped,
23 browser tests deselected, and coverage was 85.15%. `make test-e2e` passed:
23 Chromium tests, including the new 390px Others automatic-General/tag flow.
No migration, backfill, index, new tag filter/sort, or security-boundary change
was introduced. Others remains subject to the existing prohibited-content and
moderation controls.

**Create-listing UX refinement (2026-07-30):** `make check` passed: Ruff
format/lint, mypy, Django checks, migration check with no changes, 276
non-browser tests passed, 6 PostgreSQL-only tests skipped, 22 browser tests
deselected, and coverage was 85.14%. `make test-e2e` passed: 22 Chromium
tests, including 390px typed and generic state/county keyboard selection,
active-only authenticated candidates, Alaska county-equivalent behavior, and
no-horizontal-overflow checks. No migration, backfill, index, external lookup,
or privacy/policy change was introduced.

**Local generic taxonomy demo and FTS rebuild slice (2026-07-30):** after
confirming the command's DEBUG gate, ran `make seed-demo-generic-taxonomy`
locally twice. The first run created 5 synthetic published generic fixtures;
the second reported 0 created, 0 updated, and 5 unchanged. `make check` passed:
Ruff format/lint, mypy (156 source files), Django checks, migration check with
no changes, 274 non-browser tests passed, 6 PostgreSQL-only tests skipped, 20
browser tests deselected, and coverage was 85.43%. `make test-e2e` passed: 20
Chromium tests, including the seeded seller-tag search and public Tags/
Additional details smoke. No migration, index, data backfill, production-policy,
or security-boundary change was introduced.

**LST-010 seller workflow hardening (2026-07-30):** `make check` passed:
Ruff format/lint, mypy (154 source files), Django checks, and the migration
check passed with no changes detected; 270 non-browser tests passed, 6
PostgreSQL-only tests skipped, 19 browser tests deselected, and coverage was
85.24%. `make test-e2e` passed: 19 Chromium tests (276 deselected), including
the 390px typed Home advance-preservation flow and unified Home/catalog-profile
edits. No migration, backfill, index, or security-policy change was introduced.

**SRCH-004 typed public browse filters (2026-07-30):** `make check` passed:
Ruff format/lint, mypy (154 source files), Django checks, and the migration
check all passed with no changes detected; 268 non-browser tests passed, 6
PostgreSQL-only tests skipped, 19 browser tests deselected, and coverage was
85.24%. `make test-e2e` passed: 19 Chromium tests (274 deselected), including
the 390px Home, Rental, Farm & Ranch, Home & Garden compact filter groups and
the existing Autos live-filter regression. No migration, index, data backfill,
or security-policy change was introduced.

**Unified listing edit (2026-07-30):** `make check` passed: Ruff format/lint,
mypy (153 source files), Django checks, and the migration check all passed with
no changes detected; 260 non-browser tests passed, 6 PostgreSQL-only tests
skipped, 18 browser tests deselected, and coverage was 85.17%. `make test-e2e`
passed: 18 Chromium tests, including 390px edits of a Home and a generic
catalog-profile listing. The unified edit service has no migration or data
backfill; it retains the existing typed or generic detail representation.

**Bounded seller taxonomy/facts (2026-07-29):** inspected PostgreSQL SQL for
`listings.0017` (three additive relational tables, foreign keys, uniqueness, and
the deliberate controlled-tag/seller-tag indexes) and `0018` (Django state-only
blank-validation changes; PostgreSQL no-op). Applied both migrations successfully
to the local database; no category data was altered and no backfill ran.
`make check` passed: Ruff formatting/linting, mypy (153 source files), Django
checks, migration check, 257 non-browser tests passed, 6 PostgreSQL-only tests
skipped, 17 browser tests deselected, and 85.47% coverage. `make test-e2e`
passed: 17 Chromium tests.

**LST-010 category/profile completion (2026-07-29):** after confirming the
current migration state, ran `make seed-marketplace-catalog` twice. The first
local rerun updated 171 retained profile rows; the second was idempotent:
0 profiles created, 0 updated, and 171 unchanged. The local database has 171
profile rows: 102 active generic profiles, 69 inactive typed profiles, and
685 active field rows, including 668 current controlled definitions plus 17
retained historical fields. `make check` passed: Ruff formatting/linting, mypy
(153 source files), Django checks, migration check with no changes, 254
non-browser tests passed, 6 PostgreSQL-only tests skipped, 17 browser tests
deselected, and 85.44% coverage. `make test-e2e` passed: 17 Chromium tests
(260 deselected), including 390px typed Home and two unrelated generic
leaf-selection/profile flows.

**Broker attribution verification (2026-07-29):** generated and inspected
PostgreSQL `sqlmigrate listings 0016` output: it adds the bounded
`varchar(120) NOT NULL DEFAULT ''` column, then drops the database default;
there is no index, backfill, or broker contact data. Applied
`listings.0016_listing_broker_name` successfully to the local PostgreSQL
Compose database. `make check` passed: Ruff formatting/linting, mypy (153
source files), Django checks, migration check with no changes, 250 non-browser
tests passed, 6 PostgreSQL-only tests skipped, 17 browser tests deselected, and
85.34% coverage. `make test-e2e` passed: 17 Chromium tests (256 deselected),
including the 390px eligible Home field and ineligible catalog-profile absence.

**LST-010 verification (2026-07-29):** applied `catalog.0008` and
`listings.0015` to the local PostgreSQL Compose database, inspected both
PostgreSQL `sqlmigrate` outputs, and ran `make seed-marketplace-catalog`
(171 posting profiles created). `make check` passed: 244 tests passed, 6
PostgreSQL-only tests skipped, 17 browser tests deselected, and 85.01%
coverage. `make test-e2e` passed: 17 Chromium tests (249 deselected), including
the preserved generic county picker and 390px Home/catalog-profile workflow.

**Verification date:** 2026-07-27  
**Scope:** local implementation through the M12 management-console slice,
M10 mobile browse-filter/operations refinement, and M10 public
SEO/social-metadata and image-layout-stability slice

**Latest repair verification (2026-07-27):** `make check` passed with 219
non-E2E tests passed, 5 PostgreSQL-only tests skipped, and 14 browser tests
deselected; `make test-e2e` passed with 15 Chromium tests. No migration changes
were detected.

**RPT-001 workflow-hardening verification (2026-07-27):** `make check` passed:
Ruff format/lint, mypy (148 source files), Django checks, and migration check
with no changes; 222 non-E2E tests passed, 5 PostgreSQL-only tests skipped, 16
browser tests deselected, and coverage was 85.33%. `make test-e2e` passed: 16
Chromium browser tests (227 tests deselected), including public report
submission through authorized staff acknowledgement. No migration changes were
detected.

- `make check` passed: Ruff format/lint, mypy (146 source files), Django
  checks, migration check with no changes, 217 non-browser tests passed, 5
  PostgreSQL-only tests skipped, 14 browser tests deselected, and 85.52%
  coverage.
- `make test-e2e` passed: 14 Chromium tests passed (222 tests deselected),
  including 390px Menu and
  browse-filter disclosure/Escape/no-JavaScript baselines, active filter/reset
  nearby-radius retention, seller dashboard actions, management console tools,
  authenticated Create listing, and overflow guards.
- Focused SEO/media verification passed: 18 tests covering absolute canonical
  and Open Graph URL coherence, noindex query variants, social-image public
  eligibility, metadata privacy, county-equivalent naming, no-image behavior,
  and processed-image layout attributes.
- The current repository CI also runs formatting, lint, typing, Django,
  migration, PostgreSQL test, dependency-audit, browser, container, and
  Terraform validation jobs; this record does not assert a current remote CI
  result.
- Documentation-only changes after this record have not rerun application
  tests. See `dev-report.md` for the implementation/launch boundary.

## Historical starter-kit validation

**Validation date:** July 22, 2026  
**Artifact:** TheCountyPost Market Django/Cursor starter kit before application
implementation

## Passed in the artifact environment

- Required project structure and source document are present.
- 16 `SKILL.md` files have valid required frontmatter, matching folder names, unique kebab-case names, descriptions, and manual-invocation flags.
- 10 `.mdc` project rules have descriptions and application metadata.
- JSON and TOML files parse successfully.
- All scaffold Python files parse with Python 3.13 AST validation.
- Cursor scaffold installer completes a conflict-safe dry run without overwriting existing files.
- The scaffold was installed into an isolated repository copy and then installed a second time; both the initial copy and idempotent second pass completed without conflicts, and the installed copy still passed the kit validator.
- Dockerfile structural checks confirm a non-root runtime user and no automatic migration command.
- PostgreSQL 18 Compose storage is mounted at `/var/lib/postgresql`.
- Project static-file discovery is configured.
- Brand capture JavaScript passes Node syntax validation.
- Markdown local-path checks and secret-pattern review pass.
- Hidden Cursor configuration and source material are included in the packaged archive.

Primary repeatable check:

```bash
python scripts/validate_cursor_kit.py
python scripts/install_scaffold.py --dry-run
```

## Historical artifact-environment limits

A full `uv lock`/dependency installation, Django system check, migrations, pytest/Ruff/mypy/pip-audit run, and Docker build were not completed here. The environment exposes an internal Python package mirror that returned no matching distributions/temporary upstream errors, cannot resolve public PyPI directly, and has no Docker daemon/CLI.

This is an environment limitation, not evidence that those gates pass. No `uv.lock` is included, and the foundation must not be called complete until the local/CI commands below pass.

## Required first local quality gate

After resolving the P0 identity decision and installing the scaffold:

```bash
uv python install 3.13
uv lock
uv sync --frozen --all-groups
cp .env.example .env
docker compose up -d db
uv run python src/manage.py makemigrations accounts
uv run python src/manage.py sqlmigrate accounts 0001
uv run python src/manage.py migrate
make format-check
make lint
make typecheck
make django-check
make migration-check
make test
make audit
make build
```

Review the lockfile, initial migration, generated SQL, Docker build, home page, admin login route, static assets, `/health/live/`, and `/health/ready/` before committing the foundation.

## SRCH-003 PostgreSQL search validation

After applying migration `listings.0014`, rebuild the intentionally separate
search documents before exercising PostgreSQL browse:

```bash
make rebuild-listing-search-documents EXTRA_ARGS="--batch-size 250"
```

Then capture `EXPLAIN (ANALYZE, BUFFERS)` for representative statewide and
`scope=county` searches on the local nationwide fixture. Record unavailable
seed/database prerequisites rather than inventing timing. SQLite/browser tests
exercise the bounded fallback and do not validate the PostgreSQL GIN plan.

## Brand validation status

Exact visual parity is **not yet validated**. The public `thecountypost.com` host was not resolvable from the research environment. The kit intentionally uses neutral placeholders and requires approved first-party screenshots/assets/styles to populate `brand/brand-reference-manifest.json` before `/brand-parity-review` can pass.
