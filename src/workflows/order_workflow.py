"""
OrderWorkflow - Main workflow for order lifecycle management.
Handles the complete order process from receipt to shipping.
"""

import logging
from typing import Dict, Any, Optional
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ChildWorkflowError

from .activities import (
    receive_order_activity,
    validate_order_activity,
    charge_payment_activity,
    manual_review_activity
)
from .shipping_workflow import ShippingWorkflow
from .signals import CancelOrderSignal, UpdateAddressSignal

logger = logging.getLogger(__name__)


@workflow.defn
class OrderWorkflow:
    """
    Main workflow that orchestrates the complete order lifecycle.
    
    Activities:
    1. ReceiveOrder - Receive and create new order
    2. ValidateOrder - Validate order details
    3. ManualReview - Simulated human approval (timer)
    4. ChargePayment - Process payment with idempotency
    5. ShippingWorkflow - Child workflow for shipping
    
    Signals:
    - CancelOrder - Cancel order before shipping
    - UpdateAddress - Update shipping address
    
    Constraints:
    - Must complete within 15 seconds total
    """
    
    def __init__(self):
        self.order_cancelled = False
        self.cancellation_reason = None
        self.address_updated = False
        self.new_address = None
        self.current_order = None
        self.payment_id = None
    
    @workflow.run
    async def run(self, order_id: str, initial_address: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main workflow execution.
        
        Args:
            order_id: Unique identifier for the order
            initial_address: Optional initial shipping address
            
        Returns:
            Dict with order status and results
        """
        logger.info(f"Starting OrderWorkflow for order: {order_id}")
        
        try:
            # Step 1: Receive Order
            logger.info(f"Receiving order: {order_id}")
            order_result = await workflow.execute_activity(
                receive_order_activity,
                args=[order_id],
                start_to_close_timeout=timedelta(seconds=5),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=5),
                    maximum_attempts=3,
                    backoff_coefficient=2.0,
                )
            )
            self.current_order = order_result
            logger.info(f"Order received: {order_result}")
            
            # Check for cancellation after order received
            if self.order_cancelled:
                return self._handle_cancellation(order_id, "Order cancelled after receipt")
            
            # Step 2: Validate Order
            logger.info(f"Validating order: {order_id}")
            validation_result = await workflow.execute_activity(
                validate_order_activity,
                args=[order_result],
                start_to_close_timeout=timedelta(seconds=5),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=5),
                    maximum_attempts=3,
                    backoff_coefficient=2.0,
                )
            )
            logger.info(f"Order validated: {validation_result}")
            
            # Check for cancellation after validation
            if self.order_cancelled:
                return self._handle_cancellation(order_id, "Order cancelled after validation")
            
            # Step 3: Manual Review (Timer)
            logger.info(f"Starting manual review for order: {order_id}")
            review_result = await workflow.execute_activity(
                manual_review_activity,
                args=[order_result],
                start_to_close_timeout=timedelta(seconds=5),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=5),
                    maximum_attempts=2,  # Fewer retries for manual review
                    backoff_coefficient=2.0,
                )
            )
            logger.info(f"Manual review completed for order {order_id}: {review_result}")
            
            # Check for cancellation after manual review
            if self.order_cancelled:
                return self._handle_cancellation(order_id, "Order cancelled after manual review")
            
            # Step 4: Charge Payment
            self.payment_id = f"payment-{order_id}"
            logger.info(f"Charging payment for order: {order_id}, payment_id: {self.payment_id}")
            payment_result = await workflow.execute_activity(
                charge_payment_activity,
                args=[order_result, self.payment_id],
                start_to_close_timeout=timedelta(seconds=5),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=5),
                    maximum_attempts=3,
                    backoff_coefficient=2.0,
                )
            )
            logger.info(f"Payment charged for order {order_id}: {payment_result}")
            
            # Check for cancellation after payment
            if self.order_cancelled:
                return self._handle_cancellation(order_id, "Order cancelled after payment")
            
            # Step 5: Shipping (Child Workflow)
            logger.info(f"Starting shipping workflow for order: {order_id}")
            
            # Update order with new address if provided
            shipping_order = order_result.copy()
            if self.address_updated and self.new_address:
                shipping_order["address"] = self.new_address
                logger.info(f"Using updated address for order {order_id}")
            
            try:
                shipping_result = await workflow.execute_child_workflow(
                    ShippingWorkflow.run,
                    shipping_order,
                    id=f"shipping-{order_id}",
                    task_queue="shipping-tq",
                    execution_timeout=timedelta(seconds=10),
                )
                logger.info(f"Shipping completed for order {order_id}: {shipping_result}")
                
            except ChildWorkflowError as e:
                # Handle shipping failure
                error_msg = f"Shipping failed for order {order_id}: {str(e)}"
                logger.error(error_msg)
                
                # For this demo, we'll consider shipping failure as a workflow failure
                # In a real system, you might want to retry or handle differently
                return {
                    "order_id": order_id,
                    "status": "failed",
                    "error": error_msg,
                    "completed_steps": ["received", "validated", "reviewed", "payment_charged"],
                    "failed_step": "shipping"
                }
            
            # Success - return complete results
            result = {
                "order_id": order_id,
                "status": "completed",
                "order_data": order_result,
                "validation_result": validation_result,
                "review_result": review_result,
                "payment_result": payment_result,
                "shipping_result": shipping_result,
                "completed_steps": ["received", "validated", "reviewed", "payment_charged", "shipped"],
                "address_updated": self.address_updated
            }
            
            logger.info(f"OrderWorkflow completed successfully for order: {order_id}")
            return result
            
        except ActivityError as e:
            # Activity failed
            error_msg = f"Activity failed for order {order_id}: {str(e)}"
            logger.error(error_msg)
            return {
                "order_id": order_id,
                "status": "failed",
                "error": error_msg,
                "completed_steps": self._get_completed_steps(),
                "failed_step": "activity"
            }
            
        except Exception as e:
            # Unexpected error
            error_msg = f"Unexpected error in OrderWorkflow for order {order_id}: {str(e)}"
            logger.error(error_msg)
            return {
                "order_id": order_id,
                "status": "failed",
                "error": error_msg,
                "completed_steps": self._get_completed_steps(),
                "failed_step": "unexpected"
            }
    
    @workflow.signal
    async def cancel_order(self, signal: CancelOrderSignal):
        """
        Handle order cancellation signal.
        """
        logger.info(f"Received cancel order signal: {signal.reason}")
        self.order_cancelled = True
        self.cancellation_reason = signal.reason
    
    @workflow.signal
    async def update_address(self, signal: UpdateAddressSignal):
        """
        Handle address update signal.
        """
        logger.info(f"Received update address signal from: {signal.updated_by}")
        self.address_updated = True
        self.new_address = signal.new_address
    
    def _handle_cancellation(self, order_id: str, reason: str) -> Dict[str, Any]:
        """
        Handle order cancellation.
        """
        logger.info(f"Handling cancellation for order {order_id}: {reason}")
        return {
            "order_id": order_id,
            "status": "cancelled",
            "cancellation_reason": reason,
            "completed_steps": self._get_completed_steps(),
            "payment_id": self.payment_id
        }
    
    def _get_completed_steps(self) -> list:
        """
        Get list of completed steps based on current state.
        """
        steps = []
        if self.current_order:
            steps.append("received")
            steps.append("validated")
            steps.append("reviewed")
            if self.payment_id:
                steps.append("payment_charged")
        return steps
