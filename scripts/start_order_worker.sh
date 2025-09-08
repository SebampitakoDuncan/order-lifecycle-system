#!/bin/bash

# Start Order Worker Script
# This script starts only the Order Worker

echo "Starting Order Worker..."

# Check if we're in the right directory
if [ ! -f "src/workers/order_worker.py" ]; then
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

# Start the order worker
echo "Starting Order Worker on task queue: order-tq"
echo "Handles: OrderWorkflow and order activities"
echo ""
echo "Press Ctrl+C to stop the worker"
echo ""

# Run the order worker
python3 -m src.workers.order_worker

echo "Order Worker stopped."
