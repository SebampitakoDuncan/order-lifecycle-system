#!/usr/bin/env python3
"""
CLI tool for Order Lifecycle system.
Provides command-line interface for workflow management.
"""

import asyncio
import argparse
import json
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError

from workflows import OrderWorkflow
from workflows.signals import CancelOrderSignal, UpdateAddressSignal
from config import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class OrderCLI:
    """CLI for managing order workflows."""
    
    def __init__(self):
        self.client: Optional[Client] = None
    
    async def connect(self):
        """Connect to Temporal server."""
        try:
            self.client = await Client.connect(
                f"{config.TEMPORAL_HOST}:{config.TEMPORAL_PORT}",
                namespace=config.TEMPORAL_NAMESPACE
            )
            logger.info(f"Connected to Temporal server at {config.TEMPORAL_HOST}:{config.TEMPORAL_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to Temporal server: {e}")
            raise
    
    async def start_order(self, order_id: str, initial_address: Optional[Dict[str, Any]] = None):
        """Start a new order workflow."""
        if not self.client:
            await self.connect()
        
        try:
            handle = await self.client.start_workflow(
                OrderWorkflow.run,
                order_id,
                initial_address,
                id=f"order-{order_id}",
                task_queue=config.ORDER_TASK_QUEUE,
                execution_timeout=timedelta(seconds=30),
            )
            
            print(f"✅ Started order workflow: {handle.id}")
            return handle.id
            
        except Exception as e:
            logger.error(f"Failed to start order workflow: {e}")
            raise
    
    async def cancel_order(self, order_id: str, reason: str, cancelled_by: str):
        """Cancel an order workflow."""
        if not self.client:
            await self.connect()
        
        try:
            workflow_id = f"order-{order_id}"
            handle = self.client.get_workflow_handle(workflow_id)
            
            await handle.signal(
                OrderWorkflow.cancel_order,
                CancelOrderSignal(
                    reason=reason,
                    cancelled_by=cancelled_by
                )
            )
            
            print(f"✅ Sent cancel signal to order workflow: {workflow_id}")
            
        except Exception as e:
            if "not found" in str(e).lower():
                logger.error(f"Order workflow not found: {order_id}")
                raise
            logger.error(f"Failed to cancel order workflow: {e}")
            raise
    
    async def update_address(self, order_id: str, new_address: Dict[str, Any], updated_by: str):
        """Update order address."""
        if not self.client:
            await self.connect()
        
        try:
            workflow_id = f"order-{order_id}"
            handle = self.client.get_workflow_handle(workflow_id)
            
            await handle.signal(
                OrderWorkflow.update_address,
                UpdateAddressSignal(
                    new_address=new_address,
                    updated_by=updated_by
                )
            )
            
            print(f"✅ Sent address update signal to order workflow: {workflow_id}")
            
        except Exception as e:
            if "not found" in str(e).lower():
                logger.error(f"Order workflow not found: {order_id}")
                raise
            logger.error(f"Failed to update address: {e}")
            raise
    
    async def get_status(self, order_id: str):
        """Get order workflow status."""
        if not self.client:
            await self.connect()
        
        try:
            workflow_id = f"order-{order_id}"
            handle = self.client.get_workflow_handle(workflow_id)
            
            desc = await handle.describe()
            
            # Try to get result if workflow is completed
            result = None
            error = None
            status = "running"
            
            if desc.status.name == "COMPLETED":
                try:
                    result = await handle.result()
                    status = result.get("status", "completed")
                except Exception as e:
                    error = str(e)
                    status = "failed"
            elif desc.status.name == "FAILED":
                status = "failed"
                error = "Workflow execution failed"
            elif desc.status.name == "CANCELED":
                status = "cancelled"
            elif desc.status.name == "TERMINATED":
                status = "terminated"
            
            status_info = {
                "workflow_id": workflow_id,
                "order_id": order_id,
                "status": status,
                "created_at": desc.start_time.isoformat(),
                "updated_at": desc.close_time.isoformat() if desc.close_time else None,
                "completed_steps": result.get("completed_steps", []) if result else [],
                "error": error
            }
            
            print("📊 Order Status:")
            print(json.dumps(status_info, indent=2, default=str))
            
            return status_info
            
        except Exception as e:
            if "not found" in str(e).lower():
                logger.error(f"Order workflow not found: {order_id}")
                raise
            logger.error(f"Failed to get status: {e}")
            raise
    
    async def list_orders(self):
        """List all order workflows."""
        if not self.client:
            await self.connect()
        
        try:
            workflows = []
            async for workflow in self.client.list_workflows():
                if workflow.id.startswith("order-"):
                    order_id = workflow.id.replace("order-", "")
                    workflows.append({
                        "workflow_id": workflow.id,
                        "order_id": order_id,
                        "status": workflow.status.name,
                        "start_time": workflow.start_time.isoformat(),
                        "close_time": workflow.close_time.isoformat() if workflow.close_time else None
                    })
            
            print(f"📋 Found {len(workflows)} order workflows:")
            print(json.dumps(workflows, indent=2, default=str))
            
            return workflows
            
        except Exception as e:
            logger.error(f"Failed to list orders: {e}")
            raise
    
    async def test_workflow(self, order_id: str):
        """Test a complete workflow execution."""
        if not self.client:
            await self.connect()
        
        print(f"🧪 Testing workflow for order: {order_id}")
        
        try:
            # Start workflow
            workflow_id = await self.start_order(order_id)
            
            # Wait a moment
            await asyncio.sleep(2)
            
            # Check status
            await self.get_status(order_id)
            
            print("✅ Workflow test completed successfully!")
            
        except Exception as e:
            logger.error(f"Workflow test failed: {e}")
            raise


async def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="Order Lifecycle CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start order command
    start_parser = subparsers.add_parser("start", help="Start a new order workflow")
    start_parser.add_argument("order_id", help="Order ID")
    start_parser.add_argument("--address", help="Initial address (JSON string)")
    
    # Cancel order command
    cancel_parser = subparsers.add_parser("cancel", help="Cancel an order workflow")
    cancel_parser.add_argument("order_id", help="Order ID")
    cancel_parser.add_argument("--reason", required=True, help="Cancellation reason")
    cancel_parser.add_argument("--cancelled-by", required=True, help="Who is cancelling")
    
    # Update address command
    update_parser = subparsers.add_parser("update-address", help="Update order address")
    update_parser.add_argument("order_id", help="Order ID")
    update_parser.add_argument("--address", required=True, help="New address (JSON string)")
    update_parser.add_argument("--updated-by", required=True, help="Who is updating")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Get order workflow status")
    status_parser.add_argument("order_id", help="Order ID")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all order workflows")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test workflow execution")
    test_parser.add_argument("order_id", help="Order ID")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = OrderCLI()
    
    try:
        if args.command == "start":
            initial_address = None
            if args.address:
                initial_address = json.loads(args.address)
            await cli.start_order(args.order_id, initial_address)
            
        elif args.command == "cancel":
            await cli.cancel_order(args.order_id, args.reason, args.cancelled_by)
            
        elif args.command == "update-address":
            new_address = json.loads(args.address)
            await cli.update_address(args.order_id, new_address, args.updated_by)
            
        elif args.command == "status":
            await cli.get_status(args.order_id)
            
        elif args.command == "list":
            await cli.list_orders()
            
        elif args.command == "test":
            await cli.test_workflow(args.order_id)
            
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
