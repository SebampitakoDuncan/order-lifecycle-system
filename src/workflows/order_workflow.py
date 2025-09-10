"""
OrderWorkflow - Main workflow for order lifecycle management.
Handles the complete order process from receipt to shipping.
"""

from typing import Dict, Any, Optional
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ChildWorkflowError

# Do not import activities here; use activity names to avoid sandbox importing activity modules
from .shipping_workflow import ShippingWorkflow
from .signals import CancelOrderSignal, UpdateAddressSignal
# Avoid importing config in workflow code (sandbox-safe). Use constants.
ACTIVITY_TIMEOUT_SECONDS = 3
WORKFLOW_TIMEOUT_SECONDS = 15



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
        workflow.logger.info(f"Starting OrderWorkflow for order: {order_id}")
        
        try:
            # Step 1: Receive Order
            workflow.logger.info(f"Receiving order: {order_id}")
            order_result = await workflow.execute_activity(
                "receive_order_activity",
                args=[order_id],
                start_to_close_timeout=timedelta(seconds=ACTIVITY_TIMEOUT_SECONDS),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=5),
                    maximum_attempts=2,
                    backoff_coefficient=2.0,
                )
            )
            self.current_order = order_result
            workflow.logger.info(f"Order received: {order_result}")
            
            # Check for cancellation after order received
            if self.order_cancelled:
                return self._handle_cancellation(order_id, "Order cancelled after receipt")
            
            # Step 2: Validate Order
            workflow.logger.info(f"Validating order: {order_id}")
            validation_result = await workflow.execute_activity(
                "validate_order_activity",
                args=[order_result],
                start_to_close_timeout=timedelta(seconds=ACTIVITY_TIMEOUT_SECONDS),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=5),
                    maximum_attempts=2,
                    backoff_coefficient=2.0,
                )
            )
            workflow.logger.info(f"Order validated: {validation_result}")
            
            # Check for cancellation after validation
            if self.order_cancelled:
                return self._handle_cancellation(order_id, "Order cancelled after validation")
            
            # Step 3: Manual Review (Activity so it appears in Temporal UI)
            workflow.logger.info(f"Starting manual review activity for order: {order_id}")
            review_result = await workflow.execute_activity(
                "manual_review_activity",
                args=[order_result],
                start_to_close_timeout=timedelta(seconds=ACTIVITY_TIMEOUT_SECONDS),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=5),
                    maximum_attempts=2,
                    backoff_coefficient=2.0,
                )
            )
            workflow.logger.info(f"Manual review activity completed for order {order_id}: {review_result}")
            
            # Check for cancellation after manual review
            if self.order_cancelled:
                return self._handle_cancellation(order_id, "Order cancelled after manual review")
            
            # Step 4: Charge Payment
            self.payment_id = f"payment-{order_id}"
            workflow.logger.info(f"Charging payment for order: {order_id}, payment_id: {self.payment_id}")
            payment_result = await workflow.execute_activity(
                "charge_payment_activity",
                args=[order_result, self.payment_id],
                start_to_close_timeout=timedelta(seconds=ACTIVITY_TIMEOUT_SECONDS),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=5),
                    maximum_attempts=2,
                    backoff_coefficient=2.0,
                )
            )
            workflow.logger.info(f"Payment charged for order {order_id}: {payment_result}")
            
            # Check for cancellation after payment
            if self.order_cancelled:
                return self._handle_cancellation(order_id, "Order cancelled after payment")
            
            # Step 5: Shipping (Child Workflow)
            workflow.logger.info(f"Starting shipping workflow for order: {order_id}")
            
            # Update order with new address if provided
            shipping_order = order_result.copy()
            if self.address_updated and self.new_address:
                shipping_order["address"] = self.new_address
                workflow.logger.info(f"Using updated address for order {order_id}")
            
            # Execute child workflow with limited retries within time budget
            child_timeout_seconds = max(2, WORKFLOW_TIMEOUT_SECONDS - 7)
            max_shipping_retries = 1
            attempt = 0
            shipping_result = None
            while attempt <= max_shipping_retries:
                try:
                    shipping_result = await workflow.execute_child_workflow(
                        ShippingWorkflow.run,
                        shipping_order,
                        id=f"shipping-{order_id}-{attempt}",
                        task_queue="shipping-tq",
                        execution_timeout=timedelta(seconds=child_timeout_seconds),
                    )
                    workflow.logger.info(f"Shipping completed for order {order_id}: {shipping_result}")
                    break
                except ChildWorkflowError as e:
                    attempt += 1
                    workflow.logger.error(f"Shipping attempt {attempt} failed for order {order_id}: {str(e)}")
                    if attempt > max_shipping_retries:
                        error_msg = f"Shipping failed for order {order_id} after {attempt} attempts"
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
            
            workflow.logger.info(f"OrderWorkflow completed successfully for order: {order_id}")
            return result
            
        except ActivityError as e:
            # Activity failed
            error_msg = f"Activity failed for order {order_id}: {str(e)}"
            workflow.logger.error(error_msg)
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
            workflow.logger.error(error_msg)
            return {
                "order_id": order_id,
                "status": "failed",
                "error": error_msg,
                "completed_steps": self._get_completed_steps(),
                "failed_step": "unexpected"
            }
    
    @workflow.signal
    def cancel_order(self, signal: CancelOrderSignal):
        """
        Handle order cancellation signal.
        """
        workflow.logger.info(f"Received cancel order signal: {signal.reason}")
        self.order_cancelled = True
        self.cancellation_reason = signal.reason
    
    @workflow.signal
    def update_address(self, signal: UpdateAddressSignal):
        """
        Handle address update signal.
        """
        workflow.logger.info(f"Received update address signal from: {signal.updated_by}")
        self.address_updated = True
        self.new_address = signal.new_address

    @workflow.signal
    def handle_dispatch_failed(self, signal):
        """
        Handle dispatch failure signal from child workflow.
        """
        workflow.logger.info(f"Received dispatch failure from child for order: {signal.order_id} reason={signal.reason} retries={signal.retry_count}")
    
    def _handle_cancellation(self, order_id: str, reason: str) -> Dict[str, Any]:
        """
        Handle order cancellation.
        """
        workflow.logger.info(f"Handling cancellation for order {order_id}: {reason}")
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
