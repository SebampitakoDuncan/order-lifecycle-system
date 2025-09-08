#!/bin/bash

# Start Shipping Worker Script
# This script starts only the Shipping Worker

echo "Starting Shipping Worker..."

# Check if we're in the right directory
if [ ! -f "src/workers/shipping_worker.py" ]; then
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

# Start the shipping worker
echo "Starting Shipping Worker on task queue: shipping-tq"
echo "Handles: ShippingWorkflow and shipping activities"
echo ""
echo "Press Ctrl+C to stop the worker"
echo ""

# Run the shipping worker
python3 -m src.workers.shipping_worker

echo "Shipping Worker stopped."
