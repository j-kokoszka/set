.PHONY: dev test clean install-deps

# Default target: start the full dev environment
dev:
	@echo "Starting 'set' development environment..."
	python3 scripts/dev.py

# Run all backend tests
test:
	@echo "Running backend API tests..."
	@export PYTHONPATH=$${PYTHONPATH}:backend && \
	export DYNAMODB_ENDPOINT_URL=http://localhost:8001 && \
	export AWS_ACCESS_KEY_ID=local && \
	export AWS_SECRET_ACCESS_KEY=local && \
	export AWS_DEFAULT_REGION=us-east-1 && \
	export MOCK_AUTH=true && \
	pytest tests/test_api.py tests/test_workout_edit.py

# Clean up local environment
clean:
	@echo "Cleaning up..."
	-podman stop dynamodb-local
	-pkill -f uvicorn
	-pkill -f vite

# Install all dependencies (Backend & Frontend)
install-deps:
	@echo "Installing backend dependencies..."
	cd backend && ./venv/bin/pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

# Initialize local DynamoDB container manually if needed
init-db:
	@echo "Initializing DynamoDB Local..."
	podman run -d --name dynamodb-local -p 8001:8000 amazon/dynamodb-local || podman start dynamodb-local
