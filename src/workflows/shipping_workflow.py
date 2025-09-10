"""
ShippingWorkflow - Child workflow for handling order shipping.
Runs on separate task queue and signals back to parent on failure.
"""

from typing import Dict, Any
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

# Do not import activities here; use activity names to avoid sandbox importing activity modules
from .signals import DispatchFailedSignal
# Avoid importing config in workflow code (sandbox-safe). Use constants.
ACTIVITY_TIMEOUT_SECONDS = 3



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
        workflow.logger.info(f"Starting ShippingWorkflow for order: {order_id}")
        
        try:
            # Step 1: Prepare Package
            workflow.logger.info(f"Preparing package for order: {order_id}")
            package_result = await workflow.execute_activity(
                "prepare_package_activity",
                args=[order],
                start_to_close_timeout=timedelta(seconds=ACTIVITY_TIMEOUT_SECONDS),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=5),
                    maximum_attempts=2,
                    backoff_coefficient=2.0,
                )
            )
            workflow.logger.info(f"Package prepared for order {order_id}: {package_result}")
            
            # Step 2: Dispatch Carrier
            workflow.logger.info(f"Dispatching carrier for order: {order_id}")
            dispatch_result = await workflow.execute_activity(
                "dispatch_carrier_activity",
                args=[order],
                start_to_close_timeout=timedelta(seconds=ACTIVITY_TIMEOUT_SECONDS),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=5),
                    maximum_attempts=2,
                    backoff_coefficient=2.0,
                )
            )
            workflow.logger.info(f"Carrier dispatched for order {order_id}: {dispatch_result}")
            
            # Success - return results
            result = {
                "order_id": order_id,
                "status": "shipped",
                "package_result": package_result,
                "dispatch_result": dispatch_result,
                "shipping_completed": True
            }
            
            workflow.logger.info(f"ShippingWorkflow completed successfully for order: {order_id}")
            return result
            
        except ActivityError as e:
            # Activity failed - signal parent workflow and propagate error
            error_msg = f"Shipping activity failed for order {order_id}: {str(e)}"
            workflow.logger.error(error_msg)

            self.dispatch_failed = True
            self.failure_reason = error_msg
            self.retry_count += 1

            # Send signal back to parent workflow
            try:
                parent_info = workflow.info().parent
                if parent_info and parent_info.workflow_id:
                    parent_handle = workflow.get_external_workflow_handle(parent_info.workflow_id)
                    await parent_handle.signal(
                        "handle_dispatch_failed",
                        DispatchFailedSignal(reason=error_msg, order_id=order_id, retry_count=self.retry_count)
                    )
            except Exception:
                # If signaling fails, still propagate error
                pass

            # Propagate to parent (will surface as ChildWorkflowError)
            raise
            
        except Exception as e:
            # Unexpected error
            error_msg = f"Unexpected error in ShippingWorkflow for order {order_id}: {str(e)}"
            workflow.logger.error(error_msg)
            raise
    
    @workflow.signal
    def handle_dispatch_failed(self, signal: DispatchFailedSignal):
        """
        Handle dispatch failure signal (if needed for retry logic).
        """
        workflow.logger.info(f"Received dispatch failed signal for order {signal.order_id}: {signal.reason}")
        self.dispatch_failed = True
        self.failure_reason = signal.reason
        self.retry_count = signal.retry_count
