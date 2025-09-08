"""
Signal definitions for Order Lifecycle workflows.
Signals allow external systems to interact with running workflows.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class CancelOrderSignal:
    """
    Signal to cancel an order before it's shipped.
    """
    reason: str
    cancelled_by: str


@dataclass
class UpdateAddressSignal:
    """
    Signal to update the shipping address for an order.
    """
    new_address: Dict[str, Any]
    updated_by: str


@dataclass
class DispatchFailedSignal:
    """
    Signal sent from ShippingWorkflow to OrderWorkflow when dispatch fails.
    """
    reason: str
    order_id: str
    retry_count: int = 0
