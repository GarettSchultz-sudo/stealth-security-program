.PHONY: dev build test clean migrate seed deploy help

# Default target
help:
	@echo "AgentCostControl - Available commands:"
	@echo "  make dev        - Start development environment"
	@echo "  make build      - Build Docker images"
	@echo "  make test       - Run all tests"
	@echo "  make migrate    - Run database migrations"
	@echo "  make seed       - Seed database with test data"
	@echo "  make clean      - Clean up generated files"
	@echo "  make deploy     - Deploy to production"

# Development
dev:
	docker-compose up -d
	@echo "Development environment started!"
	@echo "Dashboard: http://localhost:3000"
	@echo "API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"

dev-down:
	docker-compose down

# Build
build:
	docker-compose build

# Testing
test:
	cd proxy && uv run pytest -v

test-coverage:
	cd proxy && uv run pytest --cov=app --cov-report=html

# Database
migrate:
	cd proxy && uv run alembic upgrade head

migrate-down:
	cd proxy && uv run alembic downgrade -1

migration:
	@read -p "Enter migration message: " msg; \
	cd proxy && uv run alembic revision --autogenerate -m "$$msg"

seed:
	cd proxy && uv run python scripts/seed_pricing.py

# Clean
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".venv" -exec rm -rf {} + 2>/dev/null || true

# Production
deploy:
	docker-compose -f docker-compose.prod.yml up -d --build

deploy-down:
	docker-compose -f docker-compose.prod.yml down

# Install dependencies
install-backend:
	cd proxy && uv sync

install-frontend:
	cd dashboard && npm install

install: install-backend install-frontend
