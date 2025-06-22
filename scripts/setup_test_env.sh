#!/bin/bash
# Setup script for running tests with OpenAI nano model

echo "Setting up test environment with OpenAI gpt-4.1-nano..."

# Load environment variables from .env file
if [ -f .env ]; then
    set -a  # Mark variables for export
    source .env
    set +a  # Stop marking for export
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
        -p 5433:5432 \
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

# Start application services
echo "Starting application services..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set database URL for services to use port 5433
export DATABASE_URL="postgresql+asyncpg://sr:srpass@localhost:5433/symbol_registry"

# Check if Symbol Registry is already running
if ! curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "Starting Symbol Registry service on port 8080..."
    /home/kil/.local/bin/poetry run uvicorn apps.symbol_registry.main:app --host 0.0.0.0 --port 8080 > /tmp/symbol_registry.log 2>&1 &
    echo $! > /tmp/symbol_registry.pid
    sleep 3
else
    echo "Symbol Registry already running on port 8080"
fi

# Check if RAG service is already running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "Starting RAG service on port 8000..."
    QDRANT_URL="http://localhost:6333" RAG_SQLITE_PATH="bm25.db" EMBEDDING_BACKEND="$EMBEDDING_BACKEND" EMBEDDING_MODEL="$EMBEDDING_MODEL" /home/kil/.local/bin/poetry run uvicorn apps.rag_service.api:app --host 0.0.0.0 --port 8000 > /tmp/rag_service.log 2>&1 &
    echo $! > /tmp/rag_service.pid
    sleep 3
else
    echo "RAG service already running on port 8000"
fi

echo ""
echo "All services ready! You can now run tests with:"
echo "  poetry run pytest"
echo ""
echo "To stop services later, run:"
echo "  docker stop test-postgres test-qdrant"
echo "  [ -f /tmp/symbol_registry.pid ] && kill \$(cat /tmp/symbol_registry.pid)"
echo "  [ -f /tmp/rag_service.pid ] && kill \$(cat /tmp/rag_service.pid)"