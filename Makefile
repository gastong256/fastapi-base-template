.DEFAULT_GOAL := help

SLUG ?= __PROJECT_SLUG__
IMAGE ?= __SERVICE_NAME__

.PHONY: help init install format lint typecheck test run docker-build docker-up docker-down

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

init: ## Initialize template (set PROJECT_NAME, PROJECT_SLUG, SERVICE_NAME, OWNER, DESCRIPTION)
	@bash scripts/init.sh

install: ## Install all dependencies (including dev group)
	poetry install --with dev

format: ## Format code with black + ruff --fix
	poetry run black src/ tests/
	poetry run ruff check --fix src/ tests/

lint: ## Lint with ruff (no auto-fix)
	poetry run ruff check src/ tests/
	poetry run black --check src/ tests/

typecheck: ## Static type check with pyright
	poetry run pyright src/

test: ## Run test suite with coverage
	poetry run pytest --cov=src --cov-report=term-missing

run: ## Run development server with hot-reload
	poetry run uvicorn $(SLUG).main:app --reload --host 0.0.0.0 --port 8000

docker-build: ## Build production Docker image
	docker build -t $(IMAGE):local .

docker-up: ## Start services defined in docker-compose.yml
	docker compose up --build -d

docker-down: ## Stop and remove docker-compose services
	docker compose down
