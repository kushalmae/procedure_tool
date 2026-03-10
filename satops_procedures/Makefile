# =============================================================================
# SatOps Procedures — Makefile
# =============================================================================
# Shortcuts for local development, Docker testing, and Fly.io deployment.
#
# Prerequisites:
#   Local dev  : Python 3.10+, pip
#   Docker     : Docker Engine + Compose plugin (docker compose)
#   Fly deploy : flyctl CLI (https://fly.io/docs/flyctl/install/)
# =============================================================================

.DEFAULT_GOAL := help

# ---------------------------------------------------------------------------
# Local development (bare Python + SQLite)
# ---------------------------------------------------------------------------

.PHONY: install
install: ## Install Python dependencies into current environment
	pip install -r requirements.txt

.PHONY: quickstart
quickstart: ## One-step setup: migrate + collectstatic + seed all data
	python manage.py quickstart

.PHONY: migrate
migrate: ## Run Django migrations (SQLite)
	python manage.py migrate

.PHONY: seed
seed: ## Seed the database with sample data
	python manage.py seed_all

.PHONY: superuser
superuser: ## Create a Django superuser interactively
	python manage.py createsuperuser

.PHONY: run
run: ## Start the Django dev server on http://localhost:8000
	python manage.py runserver 0.0.0.0:8000

.PHONY: collectstatic
collectstatic: ## Collect static files into staticfiles/
	python manage.py collectstatic --noinput

.PHONY: lint
lint: ## Run ruff linter
	ruff check .

.PHONY: lint-fix
lint-fix: ## Auto-fix ruff linting issues
	ruff check . --fix

.PHONY: test
test: ## Run the full test suite
	python manage.py test --verbosity=2

.PHONY: check
check: ## Run Django system checks
	python manage.py check

.PHONY: check-deploy
check-deploy: ## Run Django deployment checks (expects production env vars)
	python manage.py check --deploy

.PHONY: ci
ci: lint check test ## Run the full CI pipeline locally (lint + check + test)

# ---------------------------------------------------------------------------
# Docker Compose (local Docker + PostgreSQL — mirrors production)
# ---------------------------------------------------------------------------

.PHONY: docker-build
docker-build: ## Build the Docker image
	docker compose build

.PHONY: docker-up
docker-up: ## Start PostgreSQL + Django in Docker (foreground)
	docker compose up --build

.PHONY: docker-up-d
docker-up-d: ## Start PostgreSQL + Django in Docker (background)
	docker compose up --build -d

.PHONY: docker-down
docker-down: ## Stop and remove Docker containers
	docker compose down

.PHONY: docker-down-v
docker-down-v: ## Stop containers and delete the PostgreSQL volume (fresh start)
	docker compose down -v

.PHONY: docker-logs
docker-logs: ## Tail logs from all Docker containers
	docker compose logs -f

.PHONY: docker-shell
docker-shell: ## Open a bash shell inside the running web container
	docker compose exec web bash

.PHONY: docker-manage
docker-manage: ## Run a manage.py command inside Docker. Usage: make docker-manage CMD="seed_all"
	docker compose exec web python manage.py $(CMD)

.PHONY: docker-psql
docker-psql: ## Open a psql shell to the local PostgreSQL database
	docker compose exec db psql -U satops -d satops

# ---------------------------------------------------------------------------
# Fly.io deployment
# ---------------------------------------------------------------------------

.PHONY: fly-deploy
fly-deploy: ## Deploy to Fly.io
	fly deploy

.PHONY: fly-logs
fly-logs: ## Tail Fly.io application logs
	fly logs

.PHONY: fly-ssh
fly-ssh: ## SSH into the running Fly.io machine
	fly ssh console

.PHONY: fly-manage
fly-manage: ## Run a manage.py command on Fly.io. Usage: make fly-manage CMD="seed_all"
	fly ssh console -C "python manage.py $(CMD)"

.PHONY: fly-psql
fly-psql: ## Open a psql proxy to the Fly.io PostgreSQL database
	fly postgres connect -a satops-db

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
