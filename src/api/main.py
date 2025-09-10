"""
FastAPI application for Order Lifecycle system.
Provides REST API endpoints for workflow management.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError

from ..workflows import OrderWorkflow
from ..workflows.signals import CancelOrderSignal, UpdateAddressSignal
from ..config import config

# Configure logging
import structlog
logger = structlog.get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Order Lifecycle API",
    description="REST API for managing Temporal-based order workflows",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Temporal client
temporal_client: Optional[Client] = None


# Pydantic models
class StartOrderRequest(BaseModel):
    """Request model for starting an order workflow."""
    initial_address: Optional[Dict[str, Any]] = None


class CancelOrderRequest(BaseModel):
    """Request model for cancelling an order."""
    reason: str = Field(..., description="Reason for cancellation")
    cancelled_by: str = Field(..., description="Who is cancelling the order")


class UpdateAddressRequest(BaseModel):
    """Request model for updating order address."""
    new_address: Dict[str, Any] = Field(..., description="New shipping address")
    updated_by: str = Field(..., description="Who is updating the address")


class WorkflowStatus(BaseModel):
    """Response model for workflow status."""
    workflow_id: str
    order_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    completed_steps: List[str] = []
    created_at: datetime
    updated_at: Optional[datetime] = None


class HealthStatus(BaseModel):
    """Response model for health check."""
    status: str
    timestamp: datetime
    temporal_connected: bool
    database_connected: bool
    workers_healthy: bool


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize the Temporal client on startup."""
    global temporal_client
    try:
        temporal_client = await Client.connect(
            f"{config.TEMPORAL_HOST}:{config.TEMPORAL_PORT}",
            namespace=config.TEMPORAL_NAMESPACE
        )
        logger.info("temporal_connected", host=config.TEMPORAL_HOST, port=config.TEMPORAL_PORT)
    except Exception as e:
        logger.error("temporal_connect_failed", error=str(e))
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    global temporal_client
    # Client does not require explicit close in current SDK
    temporal_client = None
    logger.info("temporal_disconnected")


# API Endpoints

@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint."""
    try:
        # Check Temporal connection using a lightweight RPC
        temporal_connected = False
        if temporal_client:
            try:
                from temporalio.api.workflowservice.v1 import GetSystemInfoRequest
                await temporal_client.workflow_service.get_system_info(GetSystemInfoRequest())
                temporal_connected = True
            except Exception as e:
                logger.error("temporal_health_check_failed", error=str(e))
        
        # Check database connection
        database_connected = False
        try:
            from ..database.connection import get_db
            db = await get_db()
            await db.fetchval("SELECT 1")
            database_connected = True
        except Exception:
            pass
        
        # Determine overall health
        overall_healthy = temporal_connected and database_connected
        
        return HealthStatus(
            status="healthy" if overall_healthy else "unhealthy",
            timestamp=datetime.now(),
            temporal_connected=temporal_connected,
            database_connected=database_connected,
            workers_healthy=temporal_connected  # Assume workers are healthy if Temporal is connected
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthStatus(
            status="unhealthy",
            timestamp=datetime.now(),
            temporal_connected=False,
            database_connected=False,
            workers_healthy=False
        )


@app.post("/orders/{order_id}/start")
async def start_order_workflow(order_id: str, request: StartOrderRequest):
    """Start a new order workflow."""
    if not temporal_client:
        raise HTTPException(status_code=503, detail="Temporal client not available")
    
    try:
        # Start the workflow
        handle = await temporal_client.start_workflow(
            OrderWorkflow.run,
            args=[order_id, request.initial_address],
            id=f"order-{order_id}",
            task_queue=config.ORDER_TASK_QUEUE,
            execution_timeout=timedelta(seconds=config.WORKFLOW_TIMEOUT_SECONDS),
        )
        
        logger.info("workflow_started", workflow_id=handle.id, order_id=order_id)
        
        return {
            "workflow_id": handle.id,
            "order_id": order_id,
            "status": "started",
            "message": f"Order workflow started successfully"
        }
        
    except Exception as e:
        logger.error("workflow_start_failed", order_id=order_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {str(e)}")


@app.post("/orders/{order_id}/signals/cancel")
async def cancel_order(order_id: str, request: CancelOrderRequest):
    """Send cancel signal to an order workflow."""
    if not temporal_client:
        raise HTTPException(status_code=503, detail="Temporal client not available")
    
    try:
        # Get workflow handle
        workflow_id = f"order-{order_id}"
        handle = temporal_client.get_workflow_handle(workflow_id)
        
        # Send cancel signal
        await handle.signal(
            OrderWorkflow.cancel_order,
            CancelOrderSignal(
                reason=request.reason,
                cancelled_by=request.cancelled_by
            )
        )
        
        logger.info("signal_cancel_sent", workflow_id=workflow_id, order_id=order_id)
        
        return {
            "workflow_id": workflow_id,
            "order_id": order_id,
            "status": "cancelled",
            "message": f"Cancel signal sent successfully"
        }
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Order workflow not found: {order_id}")
        logger.error("signal_cancel_failed", order_id=order_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to cancel workflow: {str(e)}")


@app.post("/orders/{order_id}/signals/update-address")
async def update_order_address(order_id: str, request: UpdateAddressRequest):
    """Send address update signal to an order workflow."""
    if not temporal_client:
        raise HTTPException(status_code=503, detail="Temporal client not available")
    
    try:
        # Get workflow handle
        workflow_id = f"order-{order_id}"
        handle = temporal_client.get_workflow_handle(workflow_id)
        
        # Send address update signal
        await handle.signal(
            OrderWorkflow.update_address,
            UpdateAddressSignal(
                new_address=request.new_address,
                updated_by=request.updated_by
            )
        )
        
        logger.info("signal_update_address_sent", workflow_id=workflow_id, order_id=order_id)
        
        return {
            "workflow_id": workflow_id,
            "order_id": order_id,
            "status": "address_updated",
            "message": f"Address update signal sent successfully"
        }
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Order workflow not found: {order_id}")
        logger.error("signal_update_address_failed", order_id=order_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update address: {str(e)}")


@app.get("/orders/{order_id}/status", response_model=WorkflowStatus)
async def get_order_status(order_id: str):
    """Get the status of an order workflow."""
    if not temporal_client:
        raise HTTPException(status_code=503, detail="Temporal client not available")
    
    try:
        # Get workflow handle
        workflow_id = f"order-{order_id}"
        handle = temporal_client.get_workflow_handle(workflow_id)
        
        # Get workflow description
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
        
        return WorkflowStatus(
            workflow_id=workflow_id,
            order_id=order_id,
            status=status,
            result=result,
            error=error,
            completed_steps=result.get("completed_steps", []) if result else [],
            created_at=desc.start_time,
            updated_at=desc.close_time
        )
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Order workflow not found: {order_id}")
        logger.error("get_status_failed", order_id=order_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get workflow status: {str(e)}")


@app.get("/orders/{order_id}/history")
async def get_order_history(order_id: str):
    """Get the execution history of an order workflow."""
    if not temporal_client:
        raise HTTPException(status_code=503, detail="Temporal client not available")
    
    try:
        # Get workflow handle
        workflow_id = f"order-{order_id}"
        handle = temporal_client.get_workflow_handle(workflow_id)
        
        # Get workflow history (async iterator) and serialize minimally
        events = []
        async for event in handle.fetch_history_events():
            try:
                etype = event.event_type.name  # enum style
            except Exception:
                try:
                    etype = str(event.event_type)
                except Exception:
                    etype = "unknown"

            try:
                ts = getattr(event, "event_time", None)
                ts_str = str(ts) if ts is not None else None
            except Exception:
                ts_str = None

            events.append({
                "event_id": getattr(event, "event_id", None),
                "event_type": etype,
                "timestamp": ts_str,
            })
        
        return {
            "workflow_id": workflow_id,
            "order_id": order_id,
            "total_events": len(events),
            "events": events
        }
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Order workflow not found: {order_id}")
        logger.error("get_history_failed", order_id=order_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get workflow history: {str(e)}")


@app.get("/orders")
async def list_orders():
    """List all order workflows."""
    if not temporal_client:
        raise HTTPException(status_code=503, detail="Temporal client not available")
    
    try:
        # List workflows
        workflows = []
        async for workflow in temporal_client.list_workflows():
            if workflow.id.startswith("order-"):
                order_id = workflow.id.replace("order-", "")
                workflows.append({
                    "workflow_id": workflow.id,
                    "order_id": order_id,
                    "status": workflow.status.name,
                    "start_time": workflow.start_time,
                    "close_time": workflow.close_time
                })
        
        return {
            "total_orders": len(workflows),
            "orders": workflows
        }
        
    except Exception as e:
        logger.error(f"Failed to list order workflows: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list workflows: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
