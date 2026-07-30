# Start Here

## 1. Create the repository

Create an empty Git repository for the marketplace, copy this kit into its root, and make the first commit before generating application code.

Suggested repository name:

```text
county-post-marketplace
```

Do not place this project inside a multi-repository Cursor workspace during bootstrap. Open the repository root as the workspace so project rules, skills, and ignore settings are scoped predictably.

## 2. Install the local prerequisites

Required:

- Git
- Cursor, updated to the current stable release
- Docker Desktop or Docker Engine with Compose
- `uv` 0.11.29 or a compatible 0.11 release
- A recent Node installation only if the project later adds an asset build step
- AWS CLI and Session Manager plugin before infrastructure work
- Stripe CLI before payment integration work

The baseline application uses Python 3.13, but `uv` can install and pin it for the project.

## 3. Check Cursor configuration

Open Cursor settings and confirm:

- Project rules under `.cursor/rules` are detected.
- Project skills under `.cursor/skills` are detected.
- Agent file-edit and terminal permissions are set to **Ask** until the bootstrap is stable.
- Automatically imported third-party skills are disabled unless intentionally needed.
- The repository is the only root in the workspace.

Most supplied skills set `disable-model-invocation: true`. This keeps their descriptions out of routine context and makes them manual slash workflows. Invoke them with `/skill-name`.

## 4. Resolve the P0 product decisions

Read `docs/14-OPEN-DECISIONS.md`. Before the first business migration, resolve at least:

1. Marketplace accounts are separate at launch, or shared/federated with existing CountyPost accounts.
2. The source and approved format of the state/county reference dataset.
3. Phone verification provider and consent language.
4. Refund policy for rejected paid listings.
5. Whether the Community Board is required on the first public launch.
6. Which exact listing edits require re-moderation.
7. Approved prohibited-items policy and escalation owner.
8. Brand assets and access to the current CountyPost design source.

Use:

```text
/resolve-product-decision [decision title]
```

The skill will create or update an ADR and the open-decision register.

## 5. Bootstrap the Django foundation

Read `docs/features/FND-001-005-foundation-bootstrap.md`. The bootstrap skill may use `scripts/install_scaffold.py` as its reviewed file baseline. You can inspect the copy operation first:

```bash
python scripts/install_scaffold.py --dry-run
```

Then invoke:

```text
/bootstrap-django-marketplace
```

For a manual installation path, after the P0 identity decision is recorded:

```bash
python scripts/install_scaffold.py
uv python install 3.13
uv lock
uv sync --frozen --all-groups
cp .env.example .env
docker compose up -d db
uv run python src/manage.py makemigrations accounts
uv run python src/manage.py sqlmigrate accounts 0001
uv run python src/manage.py migrate
```

Review the generated initial migration and SQL before committing. Read `VALIDATION.md` for the gates that still need to run on a normal developer machine.

The bootstrap must stop after the foundation is healthy. It should not build listings, payments, or moderation in the same change.

Expected bootstrap result:

- `src/` layout
- split settings: base, local, test, production
- custom user model before the first migration
- PostgreSQL local environment
- health endpoints
- Docker and Compose
- `uv.lock`
- Ruff, mypy with django-stubs, pytest, coverage, and pre-commit
- GitHub Actions CI
- base templates and semantic brand-token files
- empty domain apps with clear boundaries
- an initial migration reviewed and committed

## 6. Run the foundation quality gate

Expected commands after bootstrap:

```bash
make bootstrap
make check
make test
make migration-check
make run
```

A foundation is not complete until a new developer can clone the repository, copy `.env.example`, run the documented bootstrap command, and reach both the home page and readiness endpoint.

## 7. Work from milestone slices

Begin with Milestone M0 in `docs/12-DEVELOPMENT-ROADMAP.md`. For each slice:

1. Create a feature specification from `templates/FEATURE-SPEC.md`.
2. Invoke `/plan-marketplace-feature`.
3. Review and commit the plan before code.
4. Invoke `/implement-django-feature` for the accepted slice.
5. Invoke `/test-marketplace-feature`.
6. Invoke `/review-diff`.
7. Update roadmap status, ADRs, and operational documentation.
8. Open a small pull request using `templates/PR-DESCRIPTION.md`.

The exact first-PR sequence and prompts are in `docs/21-FIRST-BUILD-SEQUENCE.md`.

## 8. First recommended Cursor prompts

After P0 decisions are documented:

```text
/bootstrap-django-marketplace
```

Then:

```text
/plan-marketplace-feature M1-A: custom marketplace identity, seller profile, and phone-verification boundary. Use docs/12-DEVELOPMENT-ROADMAP.md and do not implement yet.
```

Then:

```text
/implement-django-feature docs/features/M1-A-accounts-and-seller-profile.md
```

## 9. Rules for using Agent mode safely

- Ask Cursor to inspect before editing.
- Require a plan for changes spanning more than one app.
- Never accept a migration without reading both operations and generated SQL.
- Never allow webhook code without replay and duplicate-event tests.
- Never allow user-upload code without file-validation, authorization, and abuse cases.
- Keep PRs reversible and narrowly scoped.
- Commit before asking an agent to refactor.
- Do not mix feature work with dependency upgrades.
