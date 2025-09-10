#!/bin/bash

# Start API Server Script for Order Lifecycle System
# This script starts the FastAPI server

echo "Starting Order Lifecycle API Server..."

# Check if we're in the right directory
if [ ! -f "src/api/main.py" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

# Check if infrastructure is running
echo "Checking if infrastructure is running..."
if ! docker-compose ps | grep -q "Up"; then
    echo "Error: Infrastructure is not running. Please start it first with:"
    echo "  ./scripts/start_infrastructure.sh"
    exit 1
fi

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 5

# Start the API server
echo "Starting FastAPI server on http://localhost:8000"
echo "API Documentation available at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the API server
python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

echo "API server stopped."
