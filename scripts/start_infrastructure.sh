#!/bin/bash

# Start infrastructure script for Trellis Engineering Takehome
# Starts Temporal server and PostgreSQL database

echo "Starting infrastructure for Order Lifecycle system..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Start the infrastructure using docker-compose
echo "Starting Temporal server and PostgreSQL database..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Check if services are running
echo "Checking service status..."
docker-compose ps

echo "Infrastructure started successfully!"
echo "Temporal server: http://localhost:7233"
echo "Temporal UI: http://localhost:8080"
echo "PostgreSQL database: localhost:5432"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop services: docker-compose down"
