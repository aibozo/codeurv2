#!/bin/bash
set -e

echo "🚀 Building optimized Docker images with BuildKit..."

# Enable BuildKit
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Build the base image first
echo "📦 Building base image..."
docker build -t images/python-poetry-base:3.11 -f images/python-poetry-base/Dockerfile .

# Build all services using docker-compose with optimized config
echo "📦 Building all services with optimization..."
docker-compose -f docker-compose.yml -f docker-compose.optimized.yml build

echo "✅ Build complete!"
echo ""
echo "To use the optimized images, run:"
echo "  docker-compose -f docker-compose.yml -f docker-compose.optimized.yml up -d"