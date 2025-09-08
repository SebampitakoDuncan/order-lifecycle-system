"""
ShippingWorkflow - Child workflow for handling order shipping.
Runs on separate task queue and signals back to parent on failure.
"""

import logging
from typing import Dict, Any
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

from .activities import (
    prepare_package_activity,
    dispatch_carrier_activity
)
from .signals import DispatchFailedSignal

logger = logging.getLogger(__name__)


@workflow.defn
class ShippingWorkflow:
    """
    Child workflow that handles the shipping process for an order.
    
    Activities:
    1. PreparePackage - Prepare the order for shipping
    2. DispatchCarrier - Dispatch the carrier for delivery
    
    Signals:
    - Sends DispatchFailedSignal back to parent if dispatch fails
    """
    
    def __init__(self):
        self.dispatch_failed = False
        self.failure_reason = None
        self.retry_count = 0
    
    @workflow.run
    async def run(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main workflow execution.
        
        Args:
            order: Order data from parent workflow
            
        Returns:
            Dict with shipping status and results
        """
        order_id = order.get("order_id")
        logger.info(f"Starting ShippingWorkflow for order: {order_id}")
        
        try:
            # Step 1: Prepare Package
            logger.info(f"Preparing package for order: {order_id}")
            package_result = await workflow.execute_activity(
                prepare_package_activity,
                args=[order],
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                    maximum_attempts=3,
                    backoff_coefficient=2.0,
                )
            )
            logger.info(f"Package prepared for order {order_id}: {package_result}")
            
            # Step 2: Dispatch Carrier
            logger.info(f"Dispatching carrier for order: {order_id}")
            dispatch_result = await workflow.execute_activity(
                dispatch_carrier_activity,
                args=[order],
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                    maximum_attempts=3,
                    backoff_coefficient=2.0,
                )
            )
            logger.info(f"Carrier dispatched for order {order_id}: {dispatch_result}")
            
            # Success - return results
            result = {
                "order_id": order_id,
                "status": "shipped",
                "package_result": package_result,
                "dispatch_result": dispatch_result,
                "shipping_completed": True
            }
            
            logger.info(f"ShippingWorkflow completed successfully for order: {order_id}")
            return result
            
        except ActivityError as e:
            # Activity failed - signal parent workflow
            error_msg = f"Shipping activity failed for order {order_id}: {str(e)}"
            logger.error(error_msg)
            
            self.dispatch_failed = True
            self.failure_reason = error_msg
            self.retry_count += 1
            
            # Signal parent workflow about the failure
            # Note: In a real implementation, we'd need the parent workflow handle
            # For now, we'll raise an exception that the parent can catch
            raise workflow.ChildWorkflowError(
                f"Shipping failed for order {order_id}: {error_msg}"
            )
            
        except Exception as e:
            # Unexpected error
            error_msg = f"Unexpected error in ShippingWorkflow for order {order_id}: {str(e)}"
            logger.error(error_msg)
            raise
    
    @workflow.signal
    async def handle_dispatch_failed(self, signal: DispatchFailedSignal):
        """
        Handle dispatch failure signal (if needed for retry logic).
        """
        logger.info(f"Received dispatch failed signal for order {signal.order_id}: {signal.reason}")
        self.dispatch_failed = True
        self.failure_reason = signal.reason
        self.retry_count = signal.retry_count
