#!/bin/bash

# Start Workers Script for Order Lifecycle System
# This script starts the Temporal workers for processing workflows

echo "Starting Temporal Workers for Order Lifecycle System..."

# Check if we're in the right directory
if [ ! -f "src/workers/combined_worker.py" ]; then
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

# Wait for Temporal server to be ready
echo "Waiting for Temporal server to be ready..."
sleep 5

# Start the combined worker
echo "Starting combined worker (Order + Shipping workers)..."
echo "Workers will run on:"
echo "  - Order Worker: order-tq"
echo "  - Shipping Worker: shipping-tq"
echo ""
echo "Press Ctrl+C to stop the workers"
echo ""

# Run the combined worker
python3 -m src.workers.combined_worker

echo "Workers stopped."
