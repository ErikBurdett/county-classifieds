# Django Foundation Scaffold

This directory is a reviewed starting template, not an already-generated application. The `/bootstrap-django-marketplace` skill should copy/adapt these files into the repository root after P0 identity and infrastructure assumptions are resolved.

## Expected resulting layout

```text
.
├── .github/workflows/ci.yml
├── Dockerfile
├── Makefile
├── compose.yaml
├── pyproject.toml
├── uv.lock                    # generated and committed by uv
└── src/
    ├── manage.py
    ├── config/
    │   ├── settings/{base,local,test,production}.py
    │   ├── urls.py
    │   ├── asgi.py
    │   └── wsgi.py
    ├── apps/
    │   ├── core/
    │   └── accounts/
    ├── templates/
    └── static/
```

## Bootstrap sequence

From the repository root after copying the scaffold files:

```bash
uv python install 3.13
uv lock
uv sync --frozen --all-groups
cp .env.example .env
docker compose up -d db
uv run python src/manage.py makemigrations accounts
uv run python src/manage.py migrate
uv run python src/manage.py createsuperuser
make check
make run
```

Review the generated initial migration and its SQL before committing. The custom user model must exist before the first migration.

## Important notes

- Version ranges in `pyproject.toml` define compatibility; `uv.lock` is the exact reproducible dependency set and must be committed.
- The production Dockerfile intentionally requires `uv.lock`; create it before using Compose or building the image.
- Production does not run migrations automatically during every container startup. Run them as a deliberate ECS one-off release task.
- The PostgreSQL 18 Compose volume intentionally mounts `/var/lib/postgresql`, matching the official image’s version-specific data layout.
- The sample settings contain neutral token placeholders, not CountyPost brand values.
- Only `core` and `accounts` are registered in this minimal scaffold. Add domain apps milestone-by-milestone rather than generating unused boilerplate.
