#!/bin/bash
# Quick start script for Docker deployment

set -e

echo "🚀 Starting Grok Demo Engine..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Please create .env with your XAI_API_KEY"
    echo ""
    echo "Example:"
    echo "  XAI_API_KEY=your_api_key_here"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "Please start Docker and try again"
    exit 1
fi

echo "✅ Docker is running"
echo "✅ .env file found"
echo ""

# Build and start containers
echo "📦 Building containers..."
docker-compose build

echo ""
echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check health
if docker-compose ps | grep -q "Up (healthy)"; then
    echo ""
    echo "✅ Services are running!"
    echo ""
    echo "📍 API available at: http://localhost:8000"
    echo "📍 Health check: http://localhost:8000/health"
    echo "📍 API docs: http://localhost:8000/docs"
    echo ""
    echo "📋 Useful commands:"
    echo "  docker-compose logs -f app    # View logs"
    echo "  docker-compose ps             # Check status"
    echo "  docker-compose down           # Stop services"
    echo ""
else
    echo ""
    echo "⚠️  Services started but may not be healthy yet"
    echo "Run 'docker-compose logs -f app' to check logs"
fi
