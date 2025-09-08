"""
Combined Worker - Runs both Order and Shipping workers together.
Useful for development and testing.
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from temporalio.client import Client
from temporalio.worker import Worker

from ..workflows import (
    OrderWorkflow,
    ShippingWorkflow,
    receive_order_activity,
    validate_order_activity,
    charge_payment_activity,
    manual_review_activity,
    prepare_package_activity,
    dispatch_carrier_activity
)
from ..config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CombinedWorker:
    """
    Combined Worker that runs both Order and Shipping workers.
    """
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.order_worker: Optional[Worker] = None
        self.shipping_worker: Optional[Worker] = None
        self.shutdown_event = asyncio.Event()
    
    async def initialize(self):
        """Initialize the workers with Temporal client."""
        try:
            # Connect to Temporal server
            self.client = await Client.connect(
                f"{config.TEMPORAL_HOST}:{config.TEMPORAL_PORT}",
                namespace=config.TEMPORAL_NAMESPACE
            )
            logger.info(f"Connected to Temporal server at {config.TEMPORAL_HOST}:{config.TEMPORAL_PORT}")
            
            # Create order worker
            self.order_worker = Worker(
                self.client,
                task_queue=config.ORDER_TASK_QUEUE,
                workflows=[OrderWorkflow],
                activities=[
                    receive_order_activity,
                    validate_order_activity,
                    charge_payment_activity,
                    manual_review_activity
                ],
                max_concurrent_activities=10,
                max_concurrent_workflow_tasks=10,
            )
            
            # Create shipping worker
            self.shipping_worker = Worker(
                self.client,
                task_queue=config.SHIPPING_TASK_QUEUE,
                workflows=[ShippingWorkflow],
                activities=[
                    prepare_package_activity,
                    dispatch_carrier_activity
                ],
                max_concurrent_activities=10,
                max_concurrent_workflow_tasks=10,
            )
            
            logger.info(f"Combined worker initialized:")
            logger.info(f"  - Order worker on task queue: {config.ORDER_TASK_QUEUE}")
            logger.info(f"  - Shipping worker on task queue: {config.SHIPPING_TASK_QUEUE}")
            
        except Exception as e:
            logger.error(f"Failed to initialize combined worker: {e}")
            raise
    
    async def start(self):
        """Start both workers."""
        if not self.order_worker or not self.shipping_worker:
            raise RuntimeError("Workers not initialized. Call initialize() first.")
        
        logger.info("Starting combined worker...")
        
        try:
            # Start both workers in background
            order_task = asyncio.create_task(self.order_worker.run())
            shipping_task = asyncio.create_task(self.shipping_worker.run())
            
            logger.info("Both workers started successfully")
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            logger.info("Shutdown signal received, stopping workers...")
            
            # Cancel worker tasks
            order_task.cancel()
            shipping_task.cancel()
            
            # Wait for workers to stop gracefully
            try:
                await asyncio.wait_for(
                    asyncio.gather(order_task, shipping_task, return_exceptions=True),
                    timeout=30.0
                )
                logger.info("Workers stopped gracefully")
            except asyncio.TimeoutError:
                logger.warning("Workers did not stop within timeout, forcing shutdown")
            
        except Exception as e:
            logger.error(f"Error running combined worker: {e}")
            raise
    
    async def stop(self):
        """Stop the workers gracefully."""
        logger.info("Stopping combined worker...")
        self.shutdown_event.set()
    
    async def health_check(self) -> dict:
        """Perform health check on both workers."""
        try:
            if not self.client:
                return {"status": "unhealthy", "error": "Client not initialized"}
            
            # Check if we can connect to Temporal
            await self.client.list_workflows()
            
            return {
                "status": "healthy",
                "workers": {
                    "order": {
                        "task_queue": config.ORDER_TASK_QUEUE,
                        "workflows": ["OrderWorkflow"],
                        "activities": [
                            "receive_order_activity",
                            "validate_order_activity",
                            "charge_payment_activity",
                            "manual_review_activity"
                        ]
                    },
                    "shipping": {
                        "task_queue": config.SHIPPING_TASK_QUEUE,
                        "workflows": ["ShippingWorkflow"],
                        "activities": [
                            "prepare_package_activity",
                            "dispatch_carrier_activity"
                        ]
                    }
                }
            }
            
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


async def main():
    """Main function to run the combined worker."""
    worker = CombinedWorker()
    
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
        logger.error(f"Fatal error in combined worker: {e}")
        sys.exit(1)
    finally:
        logger.info("Combined worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
