.PHONY: lock bootstrap format format-check lint typecheck django-check production-check migration-check test test-fast check run migrate shell superuser collectstatic build audit compose-up compose-down compose-logs

UV := uv run

lock:
	uv lock

bootstrap:
	uv python install 3.13
	uv sync --all-groups
	uv run pre-commit install

format:
	$(UV) ruff format .
	$(UV) ruff check --fix .

format-check:
	$(UV) ruff format --check .

lint:
	$(UV) ruff check .

typecheck:
	$(UV) mypy src

django-check:
	$(UV) python src/manage.py check

production-check:
	$(UV) python src/manage.py check --deploy --settings=config.settings.production

migration-check:
	$(UV) python src/manage.py makemigrations --check --dry-run

# Use xdist only after the suite is known to be isolation-safe.
test:
	$(UV) pytest

test-fast:
	$(UV) pytest -q --no-cov

check: format-check lint typecheck django-check migration-check test

run:
	$(UV) python src/manage.py runserver

migrate:
	$(UV) python src/manage.py migrate

shell:
	$(UV) python src/manage.py shell

superuser:
	$(UV) python src/manage.py createsuperuser

collectstatic:
	$(UV) python src/manage.py collectstatic --noinput

build:
	docker build --tag county-post-marketplace:local .

audit:
	$(UV) pip-audit

compose-up:
	docker compose up -d db

compose-down:
	docker compose down

compose-logs:
	docker compose logs --follow db
