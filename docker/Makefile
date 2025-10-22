# Makefile for Docker Observability Stack Management

.PHONY: help build up down restart logs status clean prune dev prod health backup restore

# Default target
.DEFAULT_GOAL := help

# Variables
COMPOSE_FILE := docker-compose.observability.yml
COMPOSE_DEV := docker-compose.dev.yml
PROJECT_NAME := trading-observability

help: ## Show this help message
	@echo "Docker Observability Stack - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build all Docker images
	@echo "Building Docker images..."
	docker-compose -f $(COMPOSE_FILE) build --no-cache

up: ## Start all services
	@echo "Starting observability stack..."
	docker-compose -f $(COMPOSE_FILE) up -d
	@echo "Services started. Access:"
	@echo "  - Prometheus:  http://localhost:9090"
	@echo "  - Grafana:     http://localhost:3000"
	@echo "  - API:         http://localhost:8000"
	@echo "  - Alerts:      http://localhost:9093"

down: ## Stop all services
	@echo "Stopping observability stack..."
	docker-compose -f $(COMPOSE_FILE) down

restart: ## Restart all services
	@echo "Restarting observability stack..."
	docker-compose -f $(COMPOSE_FILE) restart

logs: ## View logs from all services
	docker-compose -f $(COMPOSE_FILE) logs -f

logs-api: ## View API logs only
	docker-compose -f $(COMPOSE_FILE) logs -f observability-api

logs-prometheus: ## View Prometheus logs only
	docker-compose -f $(COMPOSE_FILE) logs -f prometheus

logs-grafana: ## View Grafana logs only
	docker-compose -f $(COMPOSE_FILE) logs -f grafana

status: ## Show status of all services
	@echo "Service Status:"
	@docker-compose -f $(COMPOSE_FILE) ps

health: ## Check health of all services
	@echo "Health Check:"
	@echo "Prometheus:"
	@curl -s http://localhost:9090/-/healthy || echo "  UNHEALTHY"
	@echo ""
	@echo "Grafana:"
	@curl -s http://localhost:3000/api/health || echo "  UNHEALTHY"
	@echo ""
	@echo "Observability API:"
	@curl -s http://localhost:8000/health || echo "  UNHEALTHY"

clean: ## Stop and remove containers, networks
	@echo "Cleaning up..."
	docker-compose -f $(COMPOSE_FILE) down -v

prune: ## Remove all unused Docker resources
	@echo "Pruning Docker resources..."
	docker system prune -af --volumes

dev: ## Start in development mode with hot reload
	@echo "Starting in development mode..."
	docker-compose -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) up --build

prod: ## Start in production mode
	@echo "Starting in production mode..."
	docker-compose -f $(COMPOSE_FILE) up -d --build
	@echo "Production stack started."

backup: ## Backup all data volumes
	@echo "Backing up data volumes..."
	@mkdir -p ../backups
	@docker run --rm -v trading-observability_prometheus-data:/data -v $(PWD)/../backups:/backup alpine tar czf /backup/prometheus-$(shell date +%Y%m%d-%H%M%S).tar.gz -C /data .
	@docker run --rm -v trading-observability_grafana-data:/data -v $(PWD)/../backups:/backup alpine tar czf /backup/grafana-$(shell date +%Y%m%d-%H%M%S).tar.gz -C /data .
	@docker run --rm -v trading-observability_metrics-data:/data -v $(PWD)/../backups:/backup alpine tar czf /backup/metrics-$(shell date +%Y%m%d-%H%M%S).tar.gz -C /data .
	@echo "Backup completed in ../backups/"

restore: ## Restore from latest backup
	@echo "Restoring from latest backup..."
	@docker run --rm -v trading-observability_prometheus-data:/data -v $(PWD)/../backups:/backup alpine tar xzf /backup/$(shell ls -t ../backups/prometheus-*.tar.gz | head -1) -C /data
	@docker run --rm -v trading-observability_grafana-data:/data -v $(PWD)/../backups:/backup alpine tar xzf /backup/$(shell ls -t ../backups/grafana-*.tar.gz | head -1) -C /data
	@docker run --rm -v trading-observability_metrics-data:/data -v $(PWD)/../backups:/backup alpine tar xzf /backup/$(shell ls -t ../backups/metrics-*.tar.gz | head -1) -C /data
	@echo "Restore completed."

exec-api: ## Execute shell in API container
	docker-compose -f $(COMPOSE_FILE) exec observability-api /bin/bash

exec-prometheus: ## Execute shell in Prometheus container
	docker-compose -f $(COMPOSE_FILE) exec prometheus /bin/sh

exec-grafana: ## Execute shell in Grafana container
	docker-compose -f $(COMPOSE_FILE) exec grafana /bin/bash

update: ## Pull latest images
	@echo "Pulling latest images..."
	docker-compose -f $(COMPOSE_FILE) pull

validate: ## Validate Docker Compose configuration
	@echo "Validating configuration..."
	docker-compose -f $(COMPOSE_FILE) config

install: build up ## Full installation (build + start)
	@echo "Installation complete!"
	@echo "Run 'make health' to check service status"
