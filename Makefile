.PHONY: dev test clean install-deps lint build verify test-backend test-frontend lint-frontend lint-backend build-frontend init-db test-unit test-backend-unit test-frontend-unit

# Configuration
DYNAMODB_PORT ?= 8001

# Default target: start the full dev environment
dev:
	@echo "Starting 'set' development environment..."
	python3 scripts/dev.py

# Run all tests (Unit and E2E)
test: test-unit test-backend test-frontend

# Run all unit tests
test-unit: test-backend-unit test-frontend-unit

test-backend-unit:
	@echo "Running backend unit tests..."
	@export PYTHONPATH=$${PYTHONPATH}:backend && \
	export MOCK_AUTH=true && \
	export VIRTUAL_ENV=backend/venv && \
	uv run pytest tests/unit/

test-frontend-unit:
	@echo "Running frontend unit tests..."
	cd frontend && npm test

# Run all integration/E2E tests
test-backend:
	@echo "Running backend API tests..."
	@export PYTHONPATH=$${PYTHONPATH}:backend && \
	export DYNAMODB_ENDPOINT_URL=http://localhost:$(DYNAMODB_PORT) && \
	export AWS_ACCESS_KEY_ID=local && \
	export AWS_SECRET_ACCESS_KEY=local && \
	export AWS_DEFAULT_REGION=us-east-1 && \
	export MOCK_AUTH=true && \
	export VIRTUAL_ENV=backend/venv && \
	uv run python -c "from backend.database import db; db.create_table_if_not_exists()" && \
	uv run pytest tests/ --ignore=tests/unit/

test-frontend:
	@echo "Running frontend E2E tests..."
	cd frontend && npx playwright test $(PLAYWRIGHT_ARGS)

# Run all linters
lint: lint-frontend lint-backend

lint-frontend:
	@echo "Linting frontend..."
	cd frontend && npm run lint

lint-backend:
	@echo "Linting backend..."
	# Placeholder for future backend linting (e.g. ruff)
	@echo "No backend linter configured yet."

# Build the project
build: build-frontend

build-frontend:
	@echo "Building frontend..."
	cd frontend && npm run build

# Comprehensive verification (lint + test + build)
verify: lint test build
	@echo "✅ All checks passed!"

# Clean up local environment
clean:
	@echo "Cleaning up..."
	-podman stop dynamodb-local
	-pkill -f uvicorn
	-pkill -f vite

# Install all dependencies (Backend & Frontend)
install-deps:
	@echo "Installing backend dependencies..."
	cd backend && uv venv venv --allow-existing && VIRTUAL_ENV=venv uv pip install -r requirements.txt && VIRTUAL_ENV=venv uv pip install pytest httpx pytest-mock moto pytest-asyncio anyio
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

# Initialize local DynamoDB container manually if needed
init-db:
	@echo "Initializing DynamoDB Local..."
	podman run -d --name dynamodb-local -p 8001:8000 amazon/dynamodb-local || podman start dynamodb-local
