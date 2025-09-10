import asyncio
import pytest
from datetime import datetime, timezone

import src.functions.business_logic as bl


class FakeDB:
    def __init__(self):
        self.payments = {}
        self.orders = {}
        self.events = []

    async def execute(self, query: str, *args):
        q = " ".join(query.lower().split())
        if q.startswith("insert into trellis_payments"):
            payment_id, order_id, status, amount, created_at = args
            if payment_id not in self.payments:
                self.payments[payment_id] = {
                    "payment_id": payment_id,
                    "order_id": order_id,
                    "status": status,
                    "amount": amount,
                    "created_at": created_at,
                }
            return "INSERT 0 1"
        if q.startswith("update trellis_payments"):
            status, payment_id = args
            if payment_id in self.payments:
                self.payments[payment_id]["status"] = status
            return "UPDATE 1"
        if q.startswith("insert into trellis_orders"):
            order_id, state, address_json, created_at, updated_at = args
            self.orders[order_id] = {
                "id": order_id,
                "state": state,
                "address_json": address_json,
                "created_at": created_at,
                "updated_at": updated_at,
            }
            return "INSERT 0 1"
        if q.startswith("update trellis_orders"):
            # We respect WHERE state NOT IN ('shipped','cancelled') from code paths
            state, updated_at, order_id = args
            if order_id in self.orders:
                if self.orders[order_id]["state"] not in ("shipped", "cancelled"):
                    self.orders[order_id]["state"] = state
                    self.orders[order_id]["updated_at"] = updated_at
            return "UPDATE 1"
        if q.startswith("insert into trellis_events"):
            order_id, type_, payload_json, ts = args
            self.events.append({
                "order_id": order_id,
                "type": type_,
                "payload_json": payload_json,
                "ts": ts,
            })
            return "INSERT 0 1"
        return "OK"

    async def fetchrow(self, query: str, *args):
        q = " ".join(query.lower().split())
        if q.startswith("select payment_id, status, amount from trellis_payments"):
            payment_id = args[0]
            rec = self.payments.get(payment_id)
            return rec
        return None


@pytest.mark.asyncio
async def test_payment_idempotency_upsert(monkeypatch):
    async def no_flaky():
        return None
    monkeypatch.setattr(bl, "flaky_call", no_flaky)

    fake_db = FakeDB()
    async def get_db():
        return fake_db
    monkeypatch.setattr(bl, "get_db", get_db)

    order = {"order_id": "order-1", "items": [{"sku": "ABC", "qty": 2}]}

    res1 = await bl.payment_charged(order, "pay-1")
    assert res1["status"] == "charged"
    assert fake_db.payments["pay-1"]["status"] == "charged"

    res2 = await bl.payment_charged(order, "pay-1")
    assert res2["status"] == "charged"
    assert len(fake_db.payments) == 1


@pytest.mark.asyncio
async def test_order_state_transitions_idempotent(monkeypatch):
    async def no_flaky():
        return None
    monkeypatch.setattr(bl, "flaky_call", no_flaky)

    fake_db = FakeDB()
    async def get_db():
        return fake_db
    monkeypatch.setattr(bl, "get_db", get_db)

    # Seed order
    await fake_db.execute(
        """
        INSERT INTO trellis_orders (id, state, address_json, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5)
        """,
        "order-2", "received", None, datetime.now(timezone.utc), datetime.now(timezone.utc)
    )

    order = {"order_id": "order-2", "items": [{"sku": "ABC", "qty": 1}]}

    ok = await bl.order_validated(order)
    assert ok is True
    assert fake_db.orders["order-2"]["state"] == "validated"

    # Prepare package twice and ensure state does not regress
    await bl.package_prepared(order)
    state_after_first = fake_db.orders["order-2"]["state"]
    await bl.package_prepared(order)
    assert fake_db.orders["order-2"]["state"] == state_after_first

    # Ship order then ensure further updates don't override shipped
    await bl.order_shipped(order)
    assert fake_db.orders["order-2"]["state"] == "shipped"
    await bl.carrier_dispatched(order)
    assert fake_db.orders["order-2"]["state"] == "shipped"

