"""
Business logic functions for the Order Lifecycle system.
These functions implement the core business operations with database integration.
"""
import asyncio
import random
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import json

from ..database.connection import get_db
# from database.models import Order, Payment, Event  # Not used with direct asyncpg

import structlog
logger = structlog.get_logger(__name__)

# Error/Timeout Simulation Helper (You cannot change this function, which must be called from all the Function Stubs)
async def flaky_call() -> None:
    """Either raise an error or sleep long enough to trigger an activity timeout."""
    rand_num = random.random()
    if rand_num < 0.33:
        raise RuntimeError("Forced failure for testing")

    if rand_num < 0.67:
        await asyncio.sleep(300)  # Expect the activity layer to time out before this completes


async def order_received(order_id: str) -> Dict[str, Any]:
    """
    Process a new order and insert it into the database.
    
    Args:
        order_id: Unique identifier for the order
        
    Returns:
        Dict containing order information
    """
    await flaky_call()
    
    logger.info(f"Processing order received: {order_id}")
    
    # TODO: Implement DB write: insert new order record
    db_manager = await get_db()
    
    # Create order data
    order_data = {
        "order_id": order_id,
        "items": [{"sku": "ABC", "qty": 1}],
        "state": "received",
        "address_json": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    # Insert order into database
    await db_manager.execute("""
        INSERT INTO trellis_orders (id, state, address_json, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5)
    """, order_id, "received", None, order_data["created_at"], order_data["updated_at"])
    
    # Log event
    event_data = {
        "order_id": order_id,
        "items": [{"sku": "ABC", "qty": 1}],
        "state": "received",
        "address_json": None,
        "created_at": order_data["created_at"].isoformat(),
        "updated_at": order_data["updated_at"].isoformat()
    }
    await db_manager.execute("""
        INSERT INTO trellis_events (order_id, type, payload_json, ts)
        VALUES ($1, $2, $3, $4)
    """, order_id, "order_received", json.dumps(event_data), datetime.now(timezone.utc))
    
    logger.info(f"Order {order_id} successfully inserted into database")
    
    return {"order_id": order_id, "items": [{"sku": "ABC", "qty": 1}]}


async def order_validated(order: Dict[str, Any]) -> bool:
    """
    Validate an order and update its status in the database.
    
    Args:
        order: Order data dictionary
        
    Returns:
        True if validation successful
        
    Raises:
        ValueError: If order has no items
    """
    await flaky_call()
    
    order_id = order.get("order_id")
    logger.info(f"Validating order: {order_id}")
    
    # TODO: Implement DB read/write: fetch order, update validation status
    if not order.get("items"):
        raise ValueError("No items to validate")
    
    db_manager = await get_db()
    
    # Update order state to validated
    await db_manager.execute("""
        UPDATE trellis_orders 
        SET state = $1, updated_at = $2
        WHERE id = $3 AND state IN ('received','validated')
    """, "validated", datetime.now(timezone.utc), order_id)
    
    # Log validation event
    await db_manager.execute("""
        INSERT INTO trellis_events (order_id, type, payload_json, ts)
        VALUES ($1, $2, $3, $4)
    """, order_id, "order_validated", json.dumps({"items": order.get("items")}), datetime.now(timezone.utc))
    
    logger.info(f"Order {order_id} successfully validated")
    
    return True


async def payment_charged(order: Dict[str, Any], payment_id: str) -> Dict[str, Any]:
    """
    Charge payment with idempotency support.
    
    Args:
        order: Order data dictionary
        payment_id: Unique payment identifier for idempotency
        
    Returns:
        Dict containing payment status and amount
    """
    await flaky_call()
    
    order_id = order.get("order_id")
    logger.info(f"Processing payment for order {order_id} with payment_id {payment_id}")
    
    # TODO: Implement DB read/write: check payment record, insert/update payment status
    amount = sum(i.get("qty", 1) for i in order.get("items", []))
    
    db_manager = await get_db()
    
    # Insert or fetch existing payment (race-safe idempotency via upsert)
    try:
        await db_manager.execute("""
            INSERT INTO trellis_payments (payment_id, order_id, status, amount, created_at)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (payment_id) DO NOTHING
        """, payment_id, order_id, "charged", amount, datetime.now(timezone.utc))

        # Fetch the current payment record (inserted now or existing prior)
        existing_payment = await db_manager.fetchrow("""
            SELECT payment_id, status, amount FROM trellis_payments 
            WHERE payment_id = $1
        """, payment_id)

        if existing_payment and existing_payment["status"] != "charged":
            # If conflicting status, update to charged (idempotent final state)
            await db_manager.execute("""
                UPDATE trellis_payments
                SET status = $1
                WHERE payment_id = $2
            """, "charged", payment_id)
            existing_payment = await db_manager.fetchrow("""
                SELECT payment_id, status, amount FROM trellis_payments 
                WHERE payment_id = $1
            """, payment_id)

        # Update order state
        await db_manager.execute("""
            UPDATE trellis_orders 
            SET state = $1, updated_at = $2
            WHERE id = $3
        """, "payment_charged", datetime.now(timezone.utc), order_id)
        
        # Log payment event
        await db_manager.execute("""
            INSERT INTO trellis_events (order_id, type, payload_json, ts)
            VALUES ($1, $2, $3, $4)
        """, order_id, "payment_charged", json.dumps({
            "payment_id": payment_id,
            "amount": amount,
            "status": "charged"
        }), datetime.now(timezone.utc))
        
        logger.info(f"Payment {payment_id} successfully charged for order {order_id}")
        
        return {"status": existing_payment["status"] if existing_payment else "charged", "amount": amount, "payment_id": payment_id}
        
    except Exception as e:
        logger.error(f"Failed to charge payment {payment_id}: {e}")
        raise


async def order_shipped(order: Dict[str, Any]) -> str:
    """
    Mark order as shipped in the database.
    
    Args:
        order: Order data dictionary
        
    Returns:
        Status message
    """
    await flaky_call()
    
    order_id = order.get("order_id")
    logger.info(f"Shipping order: {order_id}")
    
    # TODO: Implement DB write: update order status to shipped
    db_manager = await get_db()
    
    # Update order state to shipped
    await db_manager.execute("""
        UPDATE trellis_orders 
        SET state = $1, updated_at = $2
        WHERE id = $3 AND state NOT IN ('shipped','cancelled')
    """, "shipped", datetime.now(timezone.utc), order_id)
    
    # Log shipping event
    await db_manager.execute("""
        INSERT INTO trellis_events (order_id, type, payload_json, ts)
        VALUES ($1, $2, $3, $4)
    """, order_id, "order_shipped", json.dumps({"status": "shipped"}), datetime.now(timezone.utc))
    
    logger.info(f"Order {order_id} successfully shipped")
    
    return "Shipped"


async def package_prepared(order: Dict[str, Any]) -> str:
    """
    Mark package as prepared in the database.
    
    Args:
        order: Order data dictionary
        
    Returns:
        Status message
    """
    await flaky_call()
    
    order_id = order.get("order_id")
    logger.info(f"Preparing package for order: {order_id}")
    
    # TODO: Implement DB write: mark package prepared in DB
    db_manager = await get_db()
    
    # Update order state to package_prepared
    await db_manager.execute("""
        UPDATE trellis_orders 
        SET state = $1, updated_at = $2
        WHERE id = $3 AND state NOT IN ('shipped','cancelled')
    """, "package_prepared", datetime.now(timezone.utc), order_id)
    
    # Log package preparation event
    await db_manager.execute("""
        INSERT INTO trellis_events (order_id, type, payload_json, ts)
        VALUES ($1, $2, $3, $4)
    """, order_id, "package_prepared", json.dumps({"status": "prepared"}), datetime.now(timezone.utc))
    
    logger.info(f"Package for order {order_id} successfully prepared")
    
    return "Package ready"


async def carrier_dispatched(order: Dict[str, Any]) -> str:
    """
    Record carrier dispatch in the database.
    
    Args:
        order: Order data dictionary
        
    Returns:
        Status message
    """
    await flaky_call()
    
    order_id = order.get("order_id")
    logger.info(f"Dispatching carrier for order: {order_id}")
    
    # TODO: Implement DB write: record carrier dispatch status
    db_manager = await get_db()
    
    # Update order state to carrier_dispatched
    await db_manager.execute("""
        UPDATE trellis_orders 
        SET state = $1, updated_at = $2
        WHERE id = $3 AND state NOT IN ('shipped','cancelled')
    """, "carrier_dispatched", datetime.now(timezone.utc), order_id)
    
    # Log carrier dispatch event
    await db_manager.execute("""
        INSERT INTO trellis_events (order_id, type, payload_json, ts)
        VALUES ($1, $2, $3, $4)
    """, order_id, "carrier_dispatched", json.dumps({"status": "dispatched"}), datetime.now(timezone.utc))
    
    logger.info(f"Carrier for order {order_id} successfully dispatched")
    
    return "Dispatched"
