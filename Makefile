.DEFAULT_GOAL := help

COMPOSE_DEV := docker compose --env-file core/backend/.env -f docker-compose.dev.yml
# `resolve` and `validate` import each locked plugin's backend module, so the plugins must be installed.
COMPOSE := uv run --project composer $(addprefix --with-editable ,$(wildcard plugins/*/backend examples/authentication/*/plugin)) atlas-compose

# Packages linted by .github/workflows/ruff.yml; each is passed to ruff as a
# path from the repo root, exactly like CI: ruff resolves isort's first-party
# `src` relative to the working directory when the package has no [tool.ruff].
RUFF_PACKAGES := core/backend plugin-api/python plugins/apis/backend plugins/auth-gitea/backend \
	plugins/auth-oidc/backend plugins/c4/backend plugins/database-schema/backend \
	plugins/flows/backend plugins/ingestion/backend plugins/standard-catalog/backend

# Every directory holding a manifest.yaml + lock.yaml pair.
DISTRIBUTIONS := distributions/default \
	examples/authentication/local \
	examples/authentication/oidc-keycloak \
	examples/authentication/oauth2-gitea \
	examples/authentication/custom-credentials \
	examples/ingestion \
	deploy/render

.PHONY: help docs format format-check dev-up dev-down migrate seed-demo lock lock-validate examples-up examples-down examples-list

help: ## Show this help
	@echo "Usage: make <target>"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "  %-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

docs: ## Serve the documentation site locally with live reload
	cd docs-site && uv run zensical serve

format: ## Apply ruff lint fixes (per package, as in CI) and format all Python code
	@for p in $(RUFF_PACKAGES); do \
		echo "ruff check --fix $$p"; \
		uvx ruff check --fix $$p || exit 1; \
	done
	uvx ruff format .

format-check: ## Check Python formatting without changing files
	uvx ruff format --check .

core/backend/.env:
	cp core/backend/.env.example $@

dev-up: core/backend/.env ## Build and start the development stack (applies migrations first)
	$(COMPOSE_DEV) up --build

dev-down: ## Stop the development stack
	$(COMPOSE_DEV) down

migrate: core/backend/.env ## Apply database migrations against the running development stack
	$(COMPOSE_DEV) exec backend python manage.py migrate

seed-demo: core/backend/.env ## Wipe the dev database and load the booking-platform demo catalog
	$(COMPOSE_DEV) exec backend python manage.py seed_booking_demo --yes

lock: ## Re-resolve every lock.yaml (hashes change with any edit under plugins/); use DIST=<dir> for one
	@for d in $(or $(DIST),$(DISTRIBUTIONS)); do \
		echo "resolve $$d"; \
		$(COMPOSE) resolve $$d/manifest.yaml -o $$d/lock.yaml || exit 1; \
	done

lock-validate: ## Validate every manifest/lock pair; use DIST=<dir> for one
	@for d in $(or $(DIST),$(DISTRIBUTIONS)); do \
		echo "validate $$d"; \
		$(COMPOSE) validate $$d/manifest.yaml $$d/lock.yaml || exit 1; \
	done

examples-list: ## List the runnable examples (see examples/Makefile)
	$(MAKE) -C examples list

examples-up: ## Start an example: make examples-up EXAMPLE=authentication/local
	$(MAKE) -C examples up EXAMPLE=$(EXAMPLE)

examples-down: ## Stop an example: make examples-down EXAMPLE=authentication/local
	$(MAKE) -C examples down EXAMPLE=$(EXAMPLE)
