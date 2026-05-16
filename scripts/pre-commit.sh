#!/bin/bash

# Get the list of staged files
STAGED_FILES=$(git diff --cached --name-only)

# Check if any files in the frontend/ directory have changed
if echo "$STAGED_FILES" | grep -q "^frontend/"; then
    echo "🔍 Frontend changes detected. Running frontend quality checks..."
    
    # Navigate to frontend directory
    cd frontend || exit 1
    
    # Run Lint
    echo "Running lint..."
    npm run lint || { echo "❌ Lint failed"; exit 1; }
    
    # Run Build
    echo "Running build..."
    npm run build || { echo "❌ Build failed"; exit 1; }
    
    # Run E2E tests
    echo "Running E2E tests..."
    # We use --project=chromium to keep it relatively fast
    npm run test:e2e -- --project=chromium || { echo "❌ E2E tests failed"; exit 1; }
    
    echo "✅ Frontend checks passed!"
    cd ..
fi
