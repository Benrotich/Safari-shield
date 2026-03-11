#!/bin/bash

# Safari-Shield Deployment Script

set -e

echo "🚀 Starting Safari-Shield Deployment"
echo "===================================="

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed. Aborting." >&2; exit 1; }

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | awk '/=/ {print $1}')
    echo "✅ Environment variables loaded"
else
    echo "⚠️  .env file not found, using defaults"
fi

# Build images
echo -e "\n🏗️  Building Docker images..."
docker-compose build

# Run tests
echo -e "\n🧪 Running tests..."
docker-compose run --rm api pytest tests/ -v

# Start services
echo -e "\n🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo -e "\n⏳ Waiting for services to be ready..."
sleep 10

# Check health
echo -e "\n🏥 Checking health..."
curl -f http://localhost:8000/health || { echo "Health check failed" >&2; exit 1; }

# Run database migrations
echo -e "\n🗄️  Running database migrations..."
docker-compose exec -T postgres psql -U safari -d fraud_db -f /docker-entrypoint-initdb.d/init.sql

echo -e "\n✅ Deployment complete!"
echo "📊 Services available at:"
echo "   - API: http://localhost:8000"
echo "   - Dashboard: http://localhost:8501"
echo "   - Grafana: http://localhost:3000 (admin/admin)"
echo "   - Prometheus: http://localhost:9090"
echo "   - Flower: http://localhost:5555"

# Show logs
echo -e "\n📋 Recent logs:"
docker-compose logs --tail=20