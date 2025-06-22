#!/bin/bash
# Stop test environment services

echo "Stopping test environment services..."

# Stop application services
if [ -f /tmp/symbol_registry.pid ]; then
    PID=$(cat /tmp/symbol_registry.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "Stopping Symbol Registry service (PID: $PID)..."
        kill $PID
        rm /tmp/symbol_registry.pid
    fi
fi

if [ -f /tmp/rag_service.pid ]; then
    PID=$(cat /tmp/rag_service.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "Stopping RAG service (PID: $PID)..."
        kill $PID
        rm /tmp/rag_service.pid
    fi
fi

# Stop Docker containers
echo "Stopping Docker containers..."
docker stop test-postgres test-qdrant 2>/dev/null
docker rm test-postgres test-qdrant 2>/dev/null

# Clean up log files
rm -f /tmp/symbol_registry.log /tmp/rag_service.log

echo "All services stopped."