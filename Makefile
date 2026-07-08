# Universal Analyst developer Makefile
# Supports Docker Compose v2 (`docker compose`) with legacy v1 compatibility
# (`docker-compose`) if only the legacy binary is present.

.PHONY: up down build logs test lint format prod-up prod-down

# Detect compose command: prefer v2 plugin, use the v1 binary when needed.
COMPOSE := $(shell if docker compose version >/dev/null 2>&1; then echo "docker compose"; else echo "docker-compose"; fi)

# --- Development (bind-mounts + Vite dev server) ---
up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f

# --- Production (built images + nginx) ---
prod-up:
	$(COMPOSE) -f docker-compose.prod.yml up -d --build

prod-down:
	$(COMPOSE) -f docker-compose.prod.yml down

# --- Backend quality gates ---
test:
	cd backend && pytest tests

lint:
	cd backend && ruff check .

format:
	cd backend && ruff format .