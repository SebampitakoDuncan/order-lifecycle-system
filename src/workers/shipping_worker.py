"""
Shipping Worker - Handles ShippingWorkflow and related activities.
Runs on the 'shipping-tq' task queue.
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from temporalio.client import Client
from temporalio.worker import Worker

from ..workflows import (
    ShippingWorkflow,
)
from ..workflows.activities import (
    prepare_package_activity,
    dispatch_carrier_activity
)
from ..config import config

# Configure logging
import structlog
logger = structlog.get_logger(__name__)


class ShippingWorker:
    """
    Shipping Worker that handles ShippingWorkflow and shipping-related activities.
    """
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.worker: Optional[Worker] = None
        self.shutdown_event = asyncio.Event()
    
    async def initialize(self):
        """Initialize the worker with Temporal client."""
        try:
            # Connect to Temporal server
            self.client = await Client.connect(
                f"{config.TEMPORAL_HOST}:{config.TEMPORAL_PORT}",
                namespace=config.TEMPORAL_NAMESPACE
            )
            logger.info(f"Connected to Temporal server at {config.TEMPORAL_HOST}:{config.TEMPORAL_PORT}")
            
            # Create worker
            self.worker = Worker(
                self.client,
                task_queue=config.SHIPPING_TASK_QUEUE,
                workflows=[ShippingWorkflow],
                activities=[
                    prepare_package_activity,
                    dispatch_carrier_activity
                ],
                # Configure worker settings
                max_concurrent_activities=10,
                max_concurrent_workflow_tasks=10,
            )
            
            logger.info(f"Shipping worker initialized on task queue: {config.SHIPPING_TASK_QUEUE}")
            
        except Exception as e:
            logger.error(f"Failed to initialize shipping worker: {e}")
            raise
    
    async def start(self):
        """Start the worker."""
        if not self.worker:
            raise RuntimeError("Worker not initialized. Call initialize() first.")
        
        logger.info("Starting shipping worker...")
        
        try:
            # Start worker in background
            worker_task = asyncio.create_task(self.worker.run())
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            logger.info("Shutdown signal received, stopping worker...")
            
            # Cancel worker task
            worker_task.cancel()
            
            # Wait for worker to stop gracefully
            try:
                await asyncio.wait_for(worker_task, timeout=30.0)
                logger.info("Worker stopped gracefully")
            except asyncio.TimeoutError:
                logger.warning("Worker did not stop within timeout, forcing shutdown")
            
        except Exception as e:
            logger.error(f"Error running shipping worker: {e}")
            raise
    
    async def stop(self):
        """Stop the worker gracefully."""
        logger.info("Stopping shipping worker...")
        self.shutdown_event.set()
    
    async def health_check(self) -> dict:
        """Perform health check on the worker."""
        try:
            if not self.client:
                return {"status": "unhealthy", "error": "Client not initialized"}
            
            # Check if we can connect to Temporal
            await self.client.list_workflows()
            
            return {
                "status": "healthy",
                "task_queue": config.SHIPPING_TASK_QUEUE,
                "workflows": ["ShippingWorkflow"],
                "activities": [
                    "prepare_package_activity",
                    "dispatch_carrier_activity"
                ]
            }
            
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


async def main():
    """Main function to run the shipping worker."""
    worker = ShippingWorker()
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(worker.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize and start worker
        await worker.initialize()
        await worker.start()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error in shipping worker: {e}")
        sys.exit(1)
    finally:
        logger.info("Shipping worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
