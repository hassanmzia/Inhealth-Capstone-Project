# =============================================================================
# InHealth Chronic Care Platform — Makefile
# =============================================================================
# Usage:
#   make setup        — First-time setup (copy .env, create dirs)
#   make build        — Build all Docker images
#   make up           — Start all services in background
#   make down         — Stop and remove containers
#   make logs         — Follow all service logs
#   make status       — Show running container status
#   make help         — Print this help message
# =============================================================================

# --- Configuration -----------------------------------------------------------
COMPOSE        := docker compose
COMPOSE_FILE   := docker-compose.yml
OVERRIDE_FILE  := docker-compose.override.yml

# Use override file only if it exists
ifeq ($(wildcard $(OVERRIDE_FILE)),$(OVERRIDE_FILE))
    COMPOSE_CMD := $(COMPOSE) -f $(COMPOSE_FILE) -f $(OVERRIDE_FILE)
else
    COMPOSE_CMD := $(COMPOSE) -f $(COMPOSE_FILE)
endif

PROJECT_NAME   := inhealth
ENV_FILE       := .env
ENV_EXAMPLE    := .env.example

# Container names
DJANGO_CONTAINER    := inhealth-django
POSTGRES_CONTAINER  := inhealth-postgres
NEO4J_CONTAINER     := inhealth-neo4j
QDRANT_CONTAINER    := inhealth-qdrant
REDIS_CONTAINER     := inhealth-redis
OLLAMA_BASE_URL     := http://172.168.1.95:12434
AGENTS_CONTAINER    := inhealth-agents-api
FRONTEND_CONTAINER  := inhealth-frontend

# Colors for terminal output
RED    := \033[0;31m
GREEN  := \033[0;32m
YELLOW := \033[0;33m
BLUE   := \033[0;34m
CYAN   := \033[0;36m
RESET  := \033[0m
BOLD   := \033[1m

# Default target
.DEFAULT_GOAL := help

# Mark targets that don't produce files
.PHONY: help setup build up down logs logs-django logs-agents logs-nginx \
        shell-django shell-db shell-neo4j shell-redis shell-agents \
        migrate makemigrations seed seed-postgres seed-neo4j seed-qdrant \
        test test-backend test-frontend lint lint-backend lint-frontend \
        pull-ollama list-ollama backup-db restore-db \
        restart restart-django restart-agents \
        status clean clean-volumes clean-all \
        collectstatic createsuperuser \
        build-django build-agents build-frontend \
        dev dev-backend dev-frontend \
        check-env check-health

# =============================================================================
# HELP
# =============================================================================
help:
	@echo ""
	@echo "$(BOLD)$(BLUE)InHealth Chronic Care Platform$(RESET)"
	@echo "$(BLUE)================================$(RESET)"
	@echo ""
	@echo "$(BOLD)Setup & Configuration:$(RESET)"
	@echo "  $(CYAN)make setup$(RESET)               Copy .env.example → .env, create required directories"
	@echo "  $(CYAN)make check-env$(RESET)            Validate that all required env vars are set"
	@echo ""
	@echo "$(BOLD)Docker Compose Lifecycle:$(RESET)"
	@echo "  $(CYAN)make build$(RESET)               Build all Docker images"
	@echo "  $(CYAN)make build-django$(RESET)         Build only the Django image"
	@echo "  $(CYAN)make build-agents$(RESET)         Build only the Agents API image"
	@echo "  $(CYAN)make build-frontend$(RESET)       Build only the frontend image"
	@echo "  $(CYAN)make up$(RESET)                  Start all services (detached)"
	@echo "  $(CYAN)make down$(RESET)                Stop and remove containers"
	@echo "  $(CYAN)make restart$(RESET)             Restart all services"
	@echo "  $(CYAN)make restart-django$(RESET)       Restart only Django + Celery"
	@echo "  $(CYAN)make restart-agents$(RESET)       Restart only Agents API"
	@echo "  $(CYAN)make status$(RESET)              Show container status and health"
	@echo "  $(CYAN)make check-health$(RESET)         Check health of all services"
	@echo ""
	@echo "$(BOLD)Logs:$(RESET)"
	@echo "  $(CYAN)make logs$(RESET)                Follow all service logs"
	@echo "  $(CYAN)make logs-django$(RESET)          Follow Django logs"
	@echo "  $(CYAN)make logs-agents$(RESET)          Follow Agents API logs"
	@echo "  $(CYAN)make logs-nginx$(RESET)           Follow Nginx logs"
	@echo ""
	@echo "$(BOLD)Shell Access:$(RESET)"
	@echo "  $(CYAN)make shell-django$(RESET)         Open shell in Django container"
	@echo "  $(CYAN)make shell-db$(RESET)             Open psql in PostgreSQL container"
	@echo "  $(CYAN)make shell-neo4j$(RESET)          Open cypher-shell in Neo4j container"
	@echo "  $(CYAN)make shell-redis$(RESET)          Open redis-cli in Redis container"
	@echo "  $(CYAN)make shell-agents$(RESET)         Open shell in Agents API container"
	@echo ""
	@echo "$(BOLD)Database & Migrations:$(RESET)"
	@echo "  $(CYAN)make migrate$(RESET)             Run Django database migrations"
	@echo "  $(CYAN)make makemigrations$(RESET)       Create new Django migrations"
	@echo "  $(CYAN)make seed$(RESET)                Seed all databases (postgres, neo4j, qdrant)"
	@echo "  $(CYAN)make seed-postgres$(RESET)        Seed PostgreSQL only"
	@echo "  $(CYAN)make seed-neo4j$(RESET)           Seed Neo4j only"
	@echo "  $(CYAN)make seed-qdrant$(RESET)          Seed Qdrant collections only"
	@echo "  $(CYAN)make backup-db$(RESET)            Backup PostgreSQL database"
	@echo "  $(CYAN)make restore-db$(RESET)           Restore PostgreSQL from backup"
	@echo "  $(CYAN)make collectstatic$(RESET)        Collect Django static files"
	@echo "  $(CYAN)make createsuperuser$(RESET)      Create Django superuser"
	@echo ""
	@echo "$(BOLD)Testing & Quality:$(RESET)"
	@echo "  $(CYAN)make test$(RESET)                Run all tests"
	@echo "  $(CYAN)make test-backend$(RESET)         Run Django + Agents tests"
	@echo "  $(CYAN)make test-frontend$(RESET)        Run React tests"
	@echo "  $(CYAN)make lint$(RESET)                Run all linters"
	@echo "  $(CYAN)make lint-backend$(RESET)         Run Python linters (ruff, mypy)"
	@echo "  $(CYAN)make lint-frontend$(RESET)        Run JS/TS linters (eslint, tsc)"
	@echo ""
	@echo "$(BOLD)Ollama (Local LLM):$(RESET)"
	@echo "  $(CYAN)make check-ollama$(RESET)         Verify external Ollama is reachable"
	@echo "  $(CYAN)make pull-ollama$(RESET)          Pull deepseek-r1:7b on external Ollama"
	@echo "  $(CYAN)make list-ollama$(RESET)          List models on external Ollama"
	@echo ""
	@echo "$(BOLD)Cleanup:$(RESET)"
	@echo "  $(CYAN)make clean$(RESET)               Remove containers and orphans (keep volumes)"
	@echo "  $(CYAN)make clean-volumes$(RESET)        Remove all named volumes ($(RED)DATA LOSS!$(RESET))"
	@echo "  $(CYAN)make clean-all$(RESET)            Remove everything including images ($(RED)DESTRUCTIVE!$(RESET))"
	@echo ""

# =============================================================================
# SETUP
# =============================================================================
setup: check-dirs
	@echo "$(BLUE)Setting up InHealth Chronic Care Platform...$(RESET)"
	@if [ ! -f $(ENV_FILE) ]; then \
		cp $(ENV_EXAMPLE) $(ENV_FILE); \
		echo "$(GREEN)Created .env from .env.example$(RESET)"; \
		echo "$(YELLOW)  IMPORTANT: Edit .env and fill in all required values!$(RESET)"; \
	else \
		echo "$(YELLOW).env already exists — skipping copy$(RESET)"; \
	fi
	@echo "$(GREEN)Setup complete.$(RESET)"
	@echo "$(YELLOW)Next steps:$(RESET)"
	@echo "  1. Edit $(BOLD).env$(RESET) with your configuration"
	@echo "  2. Run $(BOLD)make build$(RESET)"
	@echo "  3. Run $(BOLD)make up$(RESET)"
	@echo "  4. Run $(BOLD)make migrate$(RESET)"
	@echo "  5. Run $(BOLD)make seed$(RESET)"
	@echo "  6. Verify external Ollama: $(BOLD)make check-ollama$(RESET)"
	@echo "  7. Run $(BOLD)make createsuperuser$(RESET)"

check-dirs:
	@echo "$(BLUE)Creating required directories...$(RESET)"
	@mkdir -p \
		backend \
		agents \
		frontend \
		mcp-server \
		a2a-gateway \
		nginx/conf.d \
		scripts/postgres \
		scripts/neo4j \
		scripts/qdrant \
		config/prometheus/rules \
		config/grafana/provisioning/dashboards \
		config/grafana/provisioning/datasources \
		config/grafana/dashboards \
		config/alertmanager \
		config/qdrant \
		backups/postgres \
		backups/neo4j \
		logs
	@echo "$(GREEN)Directories created.$(RESET)"

# Validate .env exists and required keys are non-empty
check-env:
	@echo "$(BLUE)Validating environment configuration...$(RESET)"
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "$(RED)ERROR: .env file not found. Run 'make setup' first.$(RESET)"; \
		exit 1; \
	fi
	@MISSING=""; \
	for var in DJANGO_SECRET_KEY ENCRYPTION_KEY JWT_SECRET_KEY \
	           POSTGRES_PASSWORD NEO4J_PASSWORD REDIS_PASSWORD \
	           LANGFUSE_NEXTAUTH_SECRET LANGFUSE_SALT LANGFUSE_ENCRYPTION_KEY; do \
		val=$$(grep "^$$var=" $(ENV_FILE) | cut -d'=' -f2-); \
		if [ -z "$$val" ] || echo "$$val" | grep -q "change-me\|your-.*-here"; then \
			MISSING="$$MISSING $$var"; \
		fi; \
	done; \
	if [ -n "$$MISSING" ]; then \
		echo "$(RED)ERROR: The following required variables need real values in .env:$(RESET)"; \
		for v in $$MISSING; do echo "  $(YELLOW)$$v$(RESET)"; done; \
		exit 1; \
	fi
	@echo "$(GREEN)Environment configuration looks valid.$(RESET)"

# =============================================================================
# BUILD
# =============================================================================
build:
	@echo "$(BLUE)Building all Docker images...$(RESET)"
	$(COMPOSE_CMD) build --parallel
	@echo "$(GREEN)Build complete.$(RESET)"

build-django:
	@echo "$(BLUE)Building Django image...$(RESET)"
	$(COMPOSE_CMD) build django celery-worker celery-beat
	@echo "$(GREEN)Django build complete.$(RESET)"

build-agents:
	@echo "$(BLUE)Building Agents API image...$(RESET)"
	$(COMPOSE_CMD) build agents-api
	@echo "$(GREEN)Agents API build complete.$(RESET)"

build-frontend:
	@echo "$(BLUE)Building Frontend image...$(RESET)"
	$(COMPOSE_CMD) build frontend
	@echo "$(GREEN)Frontend build complete.$(RESET)"

# =============================================================================
# LIFECYCLE
# =============================================================================
up:
	@echo "$(BLUE)Starting InHealth Chronic Care Platform...$(RESET)"
	$(COMPOSE_CMD) up -d --remove-orphans
	@echo ""
	@echo "$(GREEN)Services started. Access points:$(RESET)"
	@echo "  $(CYAN)Platform (Nginx):$(RESET)    http://localhost:8788"
	@echo "  $(CYAN)Django Admin:$(RESET)        http://localhost:8788/admin/"
	@echo "  $(CYAN)API Docs:$(RESET)            http://localhost:8788/api/docs/"
	@echo "  $(CYAN)Agents API Docs:$(RESET)     http://localhost:8788/agents/docs"
	@echo "  $(CYAN)Langfuse:$(RESET)            http://localhost:3488"
	@echo "  $(CYAN)Grafana:$(RESET)             http://localhost:9391"
	@echo "  $(CYAN)Prometheus:$(RESET)          http://localhost:9390"
	@echo "  $(CYAN)Neo4j Browser:$(RESET)       http://localhost:7588"
	@echo "  $(CYAN)MinIO Console:$(RESET)       http://localhost:9589"
	@echo ""
	@make status

down:
	@echo "$(YELLOW)Stopping InHealth Chronic Care Platform...$(RESET)"
	$(COMPOSE_CMD) down --remove-orphans
	@echo "$(GREEN)All services stopped.$(RESET)"

restart:
	@echo "$(YELLOW)Restarting all services...$(RESET)"
	$(COMPOSE_CMD) restart
	@echo "$(GREEN)Restart complete.$(RESET)"

restart-django:
	@echo "$(YELLOW)Restarting Django and Celery services...$(RESET)"
	$(COMPOSE_CMD) restart django celery-worker celery-beat
	@echo "$(GREEN)Django services restarted.$(RESET)"

restart-agents:
	@echo "$(YELLOW)Restarting Agents API...$(RESET)"
	$(COMPOSE_CMD) restart agents-api
	@echo "$(GREEN)Agents API restarted.$(RESET)"

status:
	@echo "$(BLUE)Service Status:$(RESET)"
	$(COMPOSE_CMD) ps

check-health:
	@echo "$(BLUE)Checking service health...$(RESET)"
	@docker inspect --format='{{.Name}}: {{.State.Health.Status}}' \
		$(DJANGO_CONTAINER) \
		$(POSTGRES_CONTAINER) \
		$(NEO4J_CONTAINER) \
		$(QDRANT_CONTAINER) \
		$(REDIS_CONTAINER) \
		$(AGENTS_CONTAINER) \
		$(FRONTEND_CONTAINER) \
		inhealth-nginx \
		inhealth-minio \
		inhealth-langfuse-web \
		inhealth-prometheus \
		inhealth-grafana \
		2>/dev/null | sed 's/\/inhealth-//g' | sed 's/healthy/$(GREEN)healthy$(RESET)/g' | \
		sed 's/unhealthy/$(RED)unhealthy$(RESET)/g' | sed 's/starting/$(YELLOW)starting$(RESET)/g'

# =============================================================================
# LOGS
# =============================================================================
logs:
	$(COMPOSE_CMD) logs -f --tail=100

logs-django:
	$(COMPOSE_CMD) logs -f --tail=100 django celery-worker celery-beat

logs-agents:
	$(COMPOSE_CMD) logs -f --tail=100 agents-api

logs-nginx:
	$(COMPOSE_CMD) logs -f --tail=100 nginx

# =============================================================================
# SHELL ACCESS
# =============================================================================
shell-django:
	@echo "$(BLUE)Opening shell in Django container...$(RESET)"
	docker exec -it $(DJANGO_CONTAINER) /bin/bash

shell-db:
	@echo "$(BLUE)Opening psql in PostgreSQL container...$(RESET)"
	docker exec -it $(POSTGRES_CONTAINER) psql \
		-U $$(grep POSTGRES_USER $(ENV_FILE) | cut -d'=' -f2 | head -1) \
		-d $$(grep POSTGRES_DB  $(ENV_FILE) | cut -d'=' -f2 | head -1)

shell-neo4j:
	@echo "$(BLUE)Opening cypher-shell in Neo4j container...$(RESET)"
	docker exec -it $(NEO4J_CONTAINER) cypher-shell \
		-u $$(grep NEO4J_USER     $(ENV_FILE) | cut -d'=' -f2 | head -1) \
		-p $$(grep NEO4J_PASSWORD $(ENV_FILE) | cut -d'=' -f2 | head -1)

shell-redis:
	@echo "$(BLUE)Opening redis-cli in Redis container...$(RESET)"
	docker exec -it $(REDIS_CONTAINER) redis-cli \
		-a $$(grep REDIS_PASSWORD $(ENV_FILE) | cut -d'=' -f2 | head -1)

shell-agents:
	@echo "$(BLUE)Opening shell in Agents API container...$(RESET)"
	docker exec -it $(AGENTS_CONTAINER) /bin/bash

# =============================================================================
# DATABASE / MIGRATIONS
# =============================================================================
migrate:
	@echo "$(BLUE)Running Django database migrations...$(RESET)"
	docker exec $(DJANGO_CONTAINER) python manage.py migrate --noinput
	@echo "$(GREEN)Migrations complete.$(RESET)"

makemigrations:
	@echo "$(BLUE)Creating new Django migrations...$(RESET)"
	docker exec $(DJANGO_CONTAINER) python manage.py makemigrations
	@echo "$(GREEN)Migrations created.$(RESET)"

collectstatic:
	@echo "$(BLUE)Collecting Django static files...$(RESET)"
	docker exec $(DJANGO_CONTAINER) python manage.py collectstatic --noinput --clear
	@echo "$(GREEN)Static files collected.$(RESET)"

createsuperuser:
	@echo "$(BLUE)Creating Django superuser...$(RESET)"
	docker exec -it $(DJANGO_CONTAINER) python manage.py createsuperuser

# Seed all databases
seed: seed-postgres seed-neo4j seed-qdrant
	@echo "$(GREEN)All databases seeded successfully.$(RESET)"

seed-postgres:
	@echo "$(BLUE)Seeding PostgreSQL...$(RESET)"
	@if [ -f scripts/postgres/seed.py ]; then \
		docker exec $(DJANGO_CONTAINER) python manage.py shell < scripts/postgres/seed.py; \
	elif [ -f scripts/postgres/seed.sql ]; then \
		docker exec -i $(POSTGRES_CONTAINER) psql \
			-U $$(grep POSTGRES_USER $(ENV_FILE) | cut -d'=' -f2 | head -1) \
			-d $$(grep POSTGRES_DB $(ENV_FILE)  | cut -d'=' -f2 | head -1) \
			< scripts/postgres/seed.sql; \
	else \
		echo "$(YELLOW)No PostgreSQL seed file found at scripts/postgres/seed.py or seed.sql$(RESET)"; \
	fi
	@echo "$(GREEN)PostgreSQL seeded.$(RESET)"

seed-neo4j:
	@echo "$(BLUE)Seeding Neo4j...$(RESET)"
	@if [ -f scripts/neo4j/seed.cypher ]; then \
		docker exec -i $(NEO4J_CONTAINER) cypher-shell \
			-u $$(grep NEO4J_USER     $(ENV_FILE) | cut -d'=' -f2 | head -1) \
			-p $$(grep NEO4J_PASSWORD $(ENV_FILE) | cut -d'=' -f2 | head -1) \
			< scripts/neo4j/seed.cypher; \
	elif [ -f scripts/neo4j/seed.py ]; then \
		docker exec $(DJANGO_CONTAINER) python scripts/neo4j/seed.py; \
	else \
		echo "$(YELLOW)No Neo4j seed file found at scripts/neo4j/seed.cypher or seed.py$(RESET)"; \
	fi
	@echo "$(GREEN)Neo4j seeded.$(RESET)"

seed-qdrant:
	@echo "$(BLUE)Seeding Qdrant vector collections...$(RESET)"
	@if [ -f scripts/qdrant/seed.py ]; then \
		docker exec $(DJANGO_CONTAINER) python scripts/qdrant/seed.py; \
	else \
		echo "$(YELLOW)No Qdrant seed file found at scripts/qdrant/seed.py$(RESET)"; \
	fi
	@echo "$(GREEN)Qdrant seeded.$(RESET)"

# =============================================================================
# BACKUP / RESTORE
# =============================================================================
backup-db:
	@echo "$(BLUE)Backing up PostgreSQL database...$(RESET)"
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	BACKUP_FILE="backups/postgres/inhealth_$$TIMESTAMP.sql.gz"; \
	docker exec $(POSTGRES_CONTAINER) pg_dump \
		-U $$(grep POSTGRES_USER $(ENV_FILE) | cut -d'=' -f2 | head -1) \
		-d $$(grep POSTGRES_DB  $(ENV_FILE)  | cut -d'=' -f2 | head -1) \
		--no-owner --no-acl \
		| gzip > $$BACKUP_FILE; \
	echo "$(GREEN)Backup saved to $$BACKUP_FILE$(RESET)"; \
	ls -lh $$BACKUP_FILE

restore-db:
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "$(RED)ERROR: Specify backup file with: make restore-db BACKUP_FILE=backups/postgres/file.sql.gz$(RESET)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)WARNING: This will overwrite the current database. Continue? [y/N] $(RESET)"; \
	read confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		echo "$(BLUE)Restoring from $(BACKUP_FILE)...$(RESET)"; \
		gunzip -c $(BACKUP_FILE) | docker exec -i $(POSTGRES_CONTAINER) psql \
			-U $$(grep POSTGRES_USER $(ENV_FILE) | cut -d'=' -f2 | head -1) \
			-d $$(grep POSTGRES_DB  $(ENV_FILE)  | cut -d'=' -f2 | head -1); \
		echo "$(GREEN)Restore complete.$(RESET)"; \
	else \
		echo "$(YELLOW)Restore cancelled.$(RESET)"; \
	fi

# =============================================================================
# TESTING
# =============================================================================
test: test-backend test-frontend
	@echo "$(GREEN)All tests complete.$(RESET)"

test-backend:
	@echo "$(BLUE)Running backend tests (Django + Agents)...$(RESET)"
	docker exec $(DJANGO_CONTAINER) python -m pytest \
		--tb=short \
		--cov=. \
		--cov-report=term-missing \
		--cov-report=xml:coverage.xml \
		-v \
		tests/
	@echo ""
	@if [ -d agents ]; then \
		docker exec $(AGENTS_CONTAINER) python -m pytest \
			--tb=short \
			-v \
			tests/ || true; \
	fi
	@echo "$(GREEN)Backend tests complete.$(RESET)"

test-frontend:
	@echo "$(BLUE)Running frontend tests...$(RESET)"
	@if [ -d frontend ]; then \
		docker exec $(FRONTEND_CONTAINER) npm run test -- --run --reporter=verbose || true; \
	else \
		echo "$(YELLOW)No frontend directory found, skipping.$(RESET)"; \
	fi
	@echo "$(GREEN)Frontend tests complete.$(RESET)"

# =============================================================================
# LINTING / CODE QUALITY
# =============================================================================
lint: lint-backend lint-frontend
	@echo "$(GREEN)All linting complete.$(RESET)"

lint-backend:
	@echo "$(BLUE)Linting Python code (ruff + mypy)...$(RESET)"
	@if docker exec $(DJANGO_CONTAINER) which ruff > /dev/null 2>&1; then \
		docker exec $(DJANGO_CONTAINER) ruff check . --fix; \
		docker exec $(DJANGO_CONTAINER) ruff format .; \
	else \
		echo "$(YELLOW)ruff not available in container$(RESET)"; \
	fi
	@if docker exec $(DJANGO_CONTAINER) which mypy > /dev/null 2>&1; then \
		docker exec $(DJANGO_CONTAINER) mypy . --ignore-missing-imports || true; \
	fi
	@echo "$(GREEN)Python linting complete.$(RESET)"

lint-frontend:
	@echo "$(BLUE)Linting TypeScript/React (eslint + tsc)...$(RESET)"
	@if [ -d frontend ] && docker ps -q -f name=$(FRONTEND_CONTAINER) | grep -q .; then \
		docker exec $(FRONTEND_CONTAINER) npm run lint || true; \
		docker exec $(FRONTEND_CONTAINER) npm run type-check || true; \
	else \
		echo "$(YELLOW)Frontend container not running, skipping lint.$(RESET)"; \
	fi
	@echo "$(GREEN)Frontend linting complete.$(RESET)"

# =============================================================================
# OLLAMA (External LLM — running on host at 172.168.1.95:12434)
# =============================================================================
check-ollama:
	@echo "$(BLUE)Checking external Ollama at $(OLLAMA_BASE_URL)...$(RESET)"
	curl -sf $(OLLAMA_BASE_URL)/api/tags | python3 -m json.tool || \
		(echo "$(RED)ERROR: Cannot reach Ollama at $(OLLAMA_BASE_URL)$(RESET)"; exit 1)
	@echo "$(GREEN)Ollama is reachable.$(RESET)"

pull-ollama:
	@echo "$(BLUE)Pulling deepseek-r1:7b on external Ollama...$(RESET)"
	curl -sf $(OLLAMA_BASE_URL)/api/pull -d '{"name":"deepseek-r1:7b"}' | cat
	@echo "$(GREEN)Model pull requested.$(RESET)"

pull-ollama-model:
	@if [ -z "$(MODEL)" ]; then \
		echo "$(RED)ERROR: Specify model with: make pull-ollama-model MODEL=deepseek-r1:7b$(RESET)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Pulling Ollama model: $(MODEL)...$(RESET)"
	curl -sf $(OLLAMA_BASE_URL)/api/pull -d "{\"name\":\"$(MODEL)\"}" | cat

list-ollama:
	@echo "$(BLUE)Available Ollama models on $(OLLAMA_BASE_URL):$(RESET)"
	curl -sf $(OLLAMA_BASE_URL)/api/tags | python3 -c "import sys,json; [print(' -', m['name']) for m in json.load(sys.stdin).get('models',[])]"

# =============================================================================
# DEVELOPMENT HELPERS
# =============================================================================
dev:
	@echo "$(BLUE)Starting platform in development mode (with override)...$(RESET)"
	$(COMPOSE) -f $(COMPOSE_FILE) -f $(OVERRIDE_FILE) up -d --remove-orphans
	@echo "$(GREEN)Development services started.$(RESET)"

dev-backend:
	@echo "$(BLUE)Starting backend services only...$(RESET)"
	$(COMPOSE_CMD) up -d postgres redis neo4j qdrant minio
	@echo "$(GREEN)Backend infrastructure started.$(RESET)"

dev-frontend:
	@echo "$(BLUE)Starting frontend development server...$(RESET)"
	$(COMPOSE_CMD) up -d frontend nginx
	@echo "$(GREEN)Frontend started at http://localhost:8788$(RESET)"

# =============================================================================
# CLEANUP
# =============================================================================
clean:
	@echo "$(YELLOW)Removing containers and orphans (volumes preserved)...$(RESET)"
	$(COMPOSE_CMD) down --remove-orphans
	@echo "$(GREEN)Containers removed. Data volumes preserved.$(RESET)"

clean-volumes:
	@echo ""
	@echo "$(RED)$(BOLD)WARNING: This will permanently delete ALL data volumes!$(RESET)"
	@echo "$(RED)This includes: PostgreSQL, Neo4j, Qdrant, Redis, MinIO, Ollama data$(RESET)"
	@echo ""
	@printf "$(YELLOW)Type 'DELETE' to confirm: $(RESET)"; \
	read confirm; \
	if [ "$$confirm" = "DELETE" ]; then \
		$(COMPOSE_CMD) down --remove-orphans -v; \
		echo "$(GREEN)All volumes removed.$(RESET)"; \
	else \
		echo "$(YELLOW)Cancelled.$(RESET)"; \
	fi

clean-all:
	@echo ""
	@echo "$(RED)$(BOLD)WARNING: This will delete ALL containers, volumes, AND images!$(RESET)"
	@echo "$(RED)This is DESTRUCTIVE and cannot be undone.$(RESET)"
	@echo ""
	@printf "$(YELLOW)Type 'DESTROY' to confirm: $(RESET)"; \
	read confirm; \
	if [ "$$confirm" = "DESTROY" ]; then \
		$(COMPOSE_CMD) down --remove-orphans -v --rmi all; \
		docker system prune -f; \
		echo "$(GREEN)Complete cleanup done.$(RESET)"; \
	else \
		echo "$(YELLOW)Cancelled.$(RESET)"; \
	fi
