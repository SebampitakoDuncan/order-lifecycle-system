import pytest
from datetime import timedelta

from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from temporalio import workflow as wf

from src.workflows.order_workflow import OrderWorkflow
from src.workflows.shipping_workflow import ShippingWorkflow
from src.workflows.activities import (
    receive_order_activity,
    validate_order_activity,
    charge_payment_activity,
    manual_review_activity,
    prepare_package_activity,
    dispatch_carrier_activity,
)


@pytest.mark.asyncio
async def test_child_failure_escalates_and_parent_handles(monkeypatch):
    # Patch activities to deterministic behavior, with forced dispatch failure
    import src.workflows.activities as acts

    async def dummy_receive(order_id: str):
        return {"order_id": order_id, "items": [{"sku": "ABC", "qty": 1}]}

    async def dummy_validate(order: dict) -> bool:
        return True

    async def dummy_charge(order: dict, payment_id: str) -> dict:
        return {"status": "charged", "amount": 1, "payment_id": payment_id}

    async def dummy_review(order: dict) -> bool:
        return True

    async def dummy_prepare(order: dict) -> str:
        return "Package ready"

    async def fail_dispatch(order: dict) -> str:
        raise RuntimeError("forced failure for test")

    monkeypatch.setattr(acts, "order_received", dummy_receive, raising=True)
    monkeypatch.setattr(acts, "order_validated", dummy_validate, raising=True)
    monkeypatch.setattr(acts, "payment_charged", dummy_charge, raising=True)
    monkeypatch.setattr(acts, "package_prepared", dummy_prepare, raising=True)
    monkeypatch.setattr(acts, "carrier_dispatched", fail_dispatch, raising=True)
    # Avoid parent signal by making external signal a no-op.
    import temporalio.workflow as twf
    class _NoopHandle:
        async def signal(self, *args, **kwargs):
            return None
    def _fake_get_external_workflow_handle(workflow_id: str):
        return _NoopHandle()
    monkeypatch.setattr(twf, "get_external_workflow_handle", _fake_get_external_workflow_handle, raising=True)

    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="order-tq",
            workflows=[OrderWorkflow],
            activities=[
                receive_order_activity,
                validate_order_activity,
                charge_payment_activity,
                manual_review_activity,
            ],
        ):
            async with Worker(
                env.client,
                task_queue="shipping-tq",
                workflows=[ShippingWorkflow],
                activities=[
                    prepare_package_activity,
                    dispatch_carrier_activity,
                ],
            ):
                handle = await env.client.start_workflow(
                    OrderWorkflow.run,
                    args=["order-parent-child", {"street": "x"}],
                    id="order-order-parent-child",
                    task_queue="order-tq",
                    execution_timeout=timedelta(seconds=15),
                )

                result = await handle.result()
                assert result["status"] == "failed"
                assert result.get("failed_step") in ("shipping", "activity")
