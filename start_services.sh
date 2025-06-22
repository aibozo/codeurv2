#!/bin/bash
# Start services locally for testing

echo "Starting services locally..."

# Ensure we're in the virtual environment
source venv/bin/activate

# Export the correct database URL for local PostgreSQL
export DATABASE_URL="postgresql+asyncpg://sr:srpass@localhost:5433/symbol_registry"

# Start Symbol Registry service
echo "Starting Symbol Registry service on port 8080..."
cd apps/symbol_registry
python -m uvicorn main:app --host 0.0.0.0 --port 8080 &
SRM_PID=$!
cd ../..

# Start RAG service
echo "Starting RAG service on port 8000..."
export QDRANT_URL="http://localhost:6333"
export RAG_SQLITE_PATH="bm25.db"
cd apps/rag_service
python -m uvicorn api:app --host 0.0.0.0 --port 8000 &
RAG_PID=$!
cd ../..

echo "Services started:"
echo "  Symbol Registry: http://localhost:8080 (PID: $SRM_PID)"
echo "  RAG Service: http://localhost:8000 (PID: $RAG_PID)"
echo ""
echo "To stop services, run:"
echo "  kill $SRM_PID $RAG_PID"

# Keep script running
wait