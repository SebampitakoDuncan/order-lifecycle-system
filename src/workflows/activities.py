"""
Temporal activities for Order Lifecycle system.
These activities wrap the business logic functions and handle Temporal-specific concerns.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import timedelta

from temporalio import activity
from temporalio.common import RetryPolicy

from ..functions.business_logic import (
    order_received,
    order_validated, 
    payment_charged,
    order_shipped,
    package_prepared,
    carrier_dispatched
)

logger = logging.getLogger(__name__)

# Retry policy for activities
ACTIVITY_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=10),
    maximum_attempts=3,
    backoff_coefficient=2.0,
)

@activity.defn
async def receive_order_activity(order_id: str) -> Dict[str, Any]:
    """
    Activity to receive a new order.
    Calls the order_received business logic function.
    """
    logger.info(f"Starting receive_order_activity for order: {order_id}")
    
    try:
        result = await order_received(order_id)
        logger.info(f"Successfully received order: {order_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to receive order {order_id}: {e}")
        raise

@activity.defn
async def validate_order_activity(order: Dict[str, Any]) -> bool:
    """
    Activity to validate an order.
    Calls the order_validated business logic function.
    """
    order_id = order.get("order_id")
    logger.info(f"Starting validate_order_activity for order: {order_id}")
    
    try:
        result = await order_validated(order)
        logger.info(f"Successfully validated order: {order_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to validate order {order_id}: {e}")
        raise

@activity.defn
async def charge_payment_activity(order: Dict[str, Any], payment_id: str) -> Dict[str, Any]:
    """
    Activity to charge payment for an order.
    Calls the payment_charged business logic function with idempotency.
    """
    order_id = order.get("order_id")
    logger.info(f"Starting charge_payment_activity for order: {order_id}, payment: {payment_id}")
    
    try:
        result = await payment_charged(order, payment_id)
        logger.info(f"Successfully charged payment for order: {order_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to charge payment for order {order_id}: {e}")
        raise

@activity.defn
async def ship_order_activity(order: Dict[str, Any]) -> str:
    """
    Activity to ship an order.
    Calls the order_shipped business logic function.
    """
    order_id = order.get("order_id")
    logger.info(f"Starting ship_order_activity for order: {order_id}")
    
    try:
        result = await order_shipped(order)
        logger.info(f"Successfully shipped order: {order_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to ship order {order_id}: {e}")
        raise

@activity.defn
async def prepare_package_activity(order: Dict[str, Any]) -> str:
    """
    Activity to prepare a package for shipping.
    Calls the package_prepared business logic function.
    """
    order_id = order.get("order_id")
    logger.info(f"Starting prepare_package_activity for order: {order_id}")
    
    try:
        result = await package_prepared(order)
        logger.info(f"Successfully prepared package for order: {order_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to prepare package for order {order_id}: {e}")
        raise

@activity.defn
async def dispatch_carrier_activity(order: Dict[str, Any]) -> str:
    """
    Activity to dispatch carrier for order delivery.
    Calls the carrier_dispatched business logic function.
    """
    order_id = order.get("order_id")
    logger.info(f"Starting dispatch_carrier_activity for order: {order_id}")
    
    try:
        result = await carrier_dispatched(order)
        logger.info(f"Successfully dispatched carrier for order: {order_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to dispatch carrier for order {order_id}: {e}")
        raise

@activity.defn
async def manual_review_activity(order: Dict[str, Any]) -> bool:
    """
    Activity to simulate manual review/approval of an order.
    This simulates a human reviewing the order before payment.
    """
    order_id = order.get("order_id")
    logger.info(f"Starting manual_review_activity for order: {order_id}")
    
    # Simulate manual review time (1-3 seconds)
    review_time = 2.0  # seconds
    await asyncio.sleep(review_time)
    
    # For this demo, always approve the order
    # In a real system, this might involve human interaction or external approval system
    logger.info(f"Manual review completed for order: {order_id} - APPROVED")
    return True
