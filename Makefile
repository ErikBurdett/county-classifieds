.PHONY: lock bootstrap format format-check lint typecheck django-check production-check migration-check test test-fast test-e2e install-browsers check run shell migrate collectstatic build audit compose-up compose-down seed-marketplace-catalog seed-texas-autos seed-demo-marketplace seed-demo-minimal seed-demo-full seed-demo-generic-taxonomy seed-nationwide-demo-inventory seed-demo-properties seed-demo-rural-drafts seed-demo-home-goods-drafts seed-moderation-reason-codes seed-demo-billing seed-demo-staff seed-generic-demo-pricing provision-staff-groups seed-draft-policy-documents replay-payment-events cleanup-listing-media launch-smoke import-census-geography import-hud-zip-counties enable-nationwide-directory process-outbox expire-listings schedule-listing-reminders inspect-outbox rebuild-listing-search-documents terraform-fmt terraform-validate

UV := uv run
DOCKER ?= $(shell command -v docker.exe >/dev/null 2>&1 && printf '%s' docker.exe || printf '%s' docker)

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
	$(UV) python src/manage.py makemigrations --check --dry-run --settings=config.settings.test

test:
	$(UV) pytest -m "not e2e"

test-fast:
	$(UV) pytest -q --no-cov -m "not e2e"

install-browsers:
	$(UV) playwright install chromium --with-deps

test-e2e:
	DJANGO_ALLOW_ASYNC_UNSAFE=true $(UV) pytest -m e2e --no-cov

check: format-check lint typecheck django-check migration-check test

run:
	$(UV) python src/manage.py runserver

shell:
	$(UV) python src/manage.py shell

migrate:
	$(UV) python src/manage.py migrate

collectstatic:
	$(UV) python src/manage.py collectstatic --noinput

build:
	$(DOCKER) build --tag county-post-marketplace:local .

audit:
	$(UV) pip-audit

terraform-fmt:
	@if ! command -v terraform >/dev/null 2>&1; then \
		echo "Terraform is not installed; skipping terraform fmt."; \
	else \
		terraform -chdir=infrastructure/terraform fmt -check -recursive; \
	fi

terraform-validate:
	@if ! command -v terraform >/dev/null 2>&1; then \
		echo "Terraform is not installed; skipping terraform validate."; \
	else \
		terraform -chdir=infrastructure/terraform init -backend=false -input=false && \
		terraform -chdir=infrastructure/terraform validate; \
	fi

compose-up:
	$(DOCKER) compose up -d --wait db

compose-down:
	$(DOCKER) compose down

seed-texas-autos:
	$(UV) python src/manage.py seed_texas_autos

seed-marketplace-catalog:
	$(UV) python src/manage.py seed_marketplace_catalog

seed-demo-marketplace:
	$(UV) python src/manage.py seed_demo_marketplace

seed-demo-minimal: seed-texas-autos seed-demo-marketplace seed-moderation-reason-codes seed-demo-billing provision-staff-groups seed-demo-staff

seed-demo-full: seed-demo-minimal seed-marketplace-catalog seed-demo-generic-taxonomy seed-demo-properties seed-demo-rural-drafts seed-demo-home-goods-drafts seed-draft-policy-documents

seed-demo-generic-taxonomy:
	$(UV) python src/manage.py seed_demo_generic_taxonomy $(EXTRA_ARGS)

seed-nationwide-demo-inventory:
	$(UV) python src/manage.py seed_nationwide_demo_inventory

seed-demo-properties:
	$(UV) python src/manage.py seed_demo_properties

seed-demo-rural-drafts:
	$(UV) python src/manage.py seed_demo_rural_drafts

seed-demo-home-goods-drafts:
	$(UV) python src/manage.py seed_demo_home_goods_drafts

seed-moderation-reason-codes:
	$(UV) python src/manage.py seed_moderation_reason_codes

seed-demo-billing:
	$(UV) python src/manage.py seed_demo_billing

seed-generic-demo-pricing:
	$(UV) python src/manage.py seed_generic_demo_pricing

seed-demo-staff:
	$(UV) python src/manage.py seed_demo_staff

provision-staff-groups:
	$(UV) python src/manage.py provision_staff_groups

seed-draft-policy-documents:
	$(UV) python src/manage.py seed_draft_policy_documents

replay-payment-events:
	$(UV) python src/manage.py replay_payment_events

cleanup-listing-media:
	$(UV) python src/manage.py cleanup_listing_media

launch-smoke:
	$(UV) python src/manage.py launch_smoke

import-census-geography:
	@test -n "$(SOURCE)" && test -n "$(SHA256)" && test -n "$(RELEASE_DATE)"
	$(UV) python src/manage.py import_census_geography "$(SOURCE)" --expected-sha256 "$(SHA256)" --release-date "$(RELEASE_DATE)" $(EXTRA_ARGS)

import-hud-zip-counties:
	@test -n "$(SOURCE)" && test -n "$(SHA256)" && test -n "$(RELEASE_DATE)" && test -n "$(RELEASE_VERSION)"
	$(UV) python src/manage.py import_hud_zip_counties "$(SOURCE)" --expected-sha256 "$(SHA256)" --release-date "$(RELEASE_DATE)" --release-version "$(RELEASE_VERSION)" $(EXTRA_ARGS)

enable-nationwide-directory:
	$(UV) python src/manage.py enable_nationwide_directory

process-outbox:
	$(UV) python src/manage.py process_outbox $(EXTRA_ARGS)

expire-listings:
	$(UV) python src/manage.py expire_listings $(EXTRA_ARGS)

schedule-listing-reminders:
	$(UV) python src/manage.py schedule_listing_reminders

inspect-outbox:
	$(UV) python src/manage.py inspect_outbox $(EXTRA_ARGS)

rebuild-listing-search-documents:
	$(UV) python src/manage.py rebuild_listing_search_documents $(EXTRA_ARGS)
