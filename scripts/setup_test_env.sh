#!/bin/bash
# Setup script for running tests with OpenAI nano model

echo "Setting up test environment with OpenAI gpt-4.1-nano..."

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "Loaded configuration from .env file"
else
    echo "ERROR: .env file not found"
    exit 1
fi

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "ERROR: OPENAI_API_KEY not found in .env file"
    exit 1
fi

echo "Environment configured:"
echo "  LLM_BACKEND=$LLM_BACKEND"
echo "  PLANNER_MODEL=$PLANNER_MODEL"
echo "  CODING_MODEL=$CODING_MODEL"
echo "  EMBEDDING_BACKEND=$EMBEDDING_BACKEND"
echo "  EMBEDDING_MODEL=$EMBEDDING_MODEL"

# Start required services if not running
if ! docker ps | grep -q postgres; then
    echo "Starting PostgreSQL..."
    docker run -d --name test-postgres \
        -e POSTGRES_USER=sr \
        -e POSTGRES_PASSWORD=srpass \
        -e POSTGRES_DB=symbol_registry \
        -p 5432:5432 \
        postgres:16
    sleep 5
fi

if ! docker ps | grep -q qdrant; then
    echo "Starting Qdrant..."
    docker run -d --name test-qdrant \
        -p 6333:6333 \
        qdrant/qdrant:v1.9.0
    sleep 5
fi

echo "Services ready. You can now run tests with:"
echo "  poetry run pytest"