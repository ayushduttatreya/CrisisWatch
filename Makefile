# Detect docker compose command (new 'docker compose' vs old 'docker-compose')
DOCKER_COMPOSE := $(shell if docker compose version >/dev/null 2>&1; then echo "docker compose"; else echo "docker-compose"; fi)

.PHONY: help build up down logs shell test clean

help:
	@echo "CrisisWatch - Available commands:"
	@echo "  make build  - Build Docker image"
	@echo "  make up     - Start containers (detached)"
	@echo "  make down   - Stop and remove containers"
	@echo "  make logs   - View container logs"
	@echo "  make shell  - Open shell in container"
	@echo "  make test   - Run tests"
	@echo "  make clean  - Remove containers and volumes"
	@echo "  make dev    - Run without Docker (python3 main.py)"
	@echo ""
	@echo "Docker command detected: $(DOCKER_COMPOSE)"

build:
	$(DOCKER_COMPOSE) build

up:
	mkdir -p data
	$(DOCKER_COMPOSE) up -d

up-prod:
	mkdir -p data
	$(DOCKER_COMPOSE) --profile prod up -d

down:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f crisiswatch

shell:
	$(DOCKER_COMPOSE) exec crisiswatch /bin/sh

test:
	$(DOCKER_COMPOSE) exec crisiswatch python -m pytest tests/ -v

clean:
	$(DOCKER_COMPOSE) down -v
	docker rmi crisiswatch_crisiswatch 2>/dev/null || true

# Development without Docker
dev:
	python3 main.py

# Quick rebuild
rebuild: down build up
