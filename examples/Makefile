.DEFAULT_GOAL := help

EXAMPLES := authentication/local authentication/oidc-keycloak authentication/oauth2-gitea authentication/custom-credentials ingestion

.PHONY: help list up down ps smoke

help: ## Show this help
	@echo "Usage: make <target> EXAMPLE=<name>"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "  %-8s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@$(MAKE) --no-print-directory list

list: ## List the available EXAMPLE names
	@echo "Available examples:"
	@for e in $(EXAMPLES); do echo "  $$e"; done

up: guard-EXAMPLE ## Build and start an example: make up EXAMPLE=authentication/local
	cd $(EXAMPLE) && [ -f .env ] || cp .env.example .env
	cd $(EXAMPLE) && docker compose config --quiet
	cd $(EXAMPLE) && docker compose up --build -d
	cd $(EXAMPLE) && docker compose ps

down: guard-EXAMPLE ## Stop an example and remove its volumes: make down EXAMPLE=authentication/local
	cd $(EXAMPLE) && docker compose down --volumes --remove-orphans

ps: guard-EXAMPLE ## Show an example's container status: make ps EXAMPLE=authentication/local
	cd $(EXAMPLE) && docker compose ps

smoke: guard-EXAMPLE ## Run an example's smoke test: make smoke EXAMPLE=authentication/local
	cd $(EXAMPLE) && ./smoke.sh

guard-EXAMPLE:
	@test -n "$(EXAMPLE)" || { \
		echo "EXAMPLE is required, e.g. make $(MAKECMDGOALS) EXAMPLE=authentication/local" >&2; \
		$(MAKE) --no-print-directory list >&2; \
		exit 1; \
	}
