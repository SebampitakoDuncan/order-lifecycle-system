#!/bin/bash

# Start infrastructure script for Trellis Engineering Takehome
# Starts Temporal server and PostgreSQL database

echo "🚀 Starting infrastructure for Order Lifecycle system..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Clean up any existing containers to avoid conflicts
echo "🧹 Cleaning up any existing containers..."
docker-compose down -v 2>/dev/null || true

# Remove any containers that might conflict with our ports
echo "🔍 Checking for port conflicts..."
if docker ps --format "table {{.Names}}\t{{.Ports}}" | grep -E ":(7233|8080|5432)" > /dev/null; then
    echo "⚠️  Warning: Some ports (7233, 8080, 5432) are already in use."
    echo "   This might cause conflicts. Consider stopping other services using these ports."
fi

# Start the infrastructure using docker-compose
echo "🐳 Starting Temporal server, UI, and PostgreSQL database..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start (this may take 30-60 seconds)..."
sleep 15

# Check if services are running
echo "📊 Checking service status..."
docker-compose ps

# Wait a bit more for Temporal to fully initialize
echo "⏳ Waiting for Temporal to complete initialization..."
sleep 15

# Test if services are responding
echo "🔍 Testing service connectivity..."

# Test PostgreSQL
if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo "✅ PostgreSQL is ready"
else
    echo "⚠️  PostgreSQL is still starting up..."
fi

# Test Temporal server
if curl -s http://localhost:7233 > /dev/null 2>&1; then
    echo "✅ Temporal server is responding"
else
    echo "⚠️  Temporal server is still starting up..."
fi

# Test Temporal UI
if curl -s http://localhost:8080 > /dev/null 2>&1; then
    echo "✅ Temporal UI is responding"
else
    echo "⚠️  Temporal UI is still starting up..."
fi

echo ""
echo "🎉 Infrastructure started successfully!"
echo ""
echo "📍 Service URLs:"
echo "   • Temporal server: http://localhost:7233"
echo "   • Temporal UI: http://localhost:8080"
echo "   • PostgreSQL database: localhost:5432"
echo ""
echo "🔧 Management commands:"
echo "   • View logs: docker-compose logs -f"
echo "   • Stop services: docker-compose down"
echo "   • Restart services: docker-compose restart"
echo ""
echo "⏰ Note: Services may take 1-2 minutes to fully initialize."
echo "   If you encounter connection errors, wait a bit longer and try again."
