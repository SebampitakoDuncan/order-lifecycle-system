# Trellis Eng Takehome (PUBLIC)

# Temporal Take‑Home: **Function Stubs Only** (Python) with DB Read/Write Notes

## Goal

Use [Temporal's open‑source SDK](https://github.com/temporalio/temporal) and dev server to orchestrate an **Order Lifecycle**. You will design the **workflows** and **activities**. This doc supplies **function implementations** that simulate failures and timeouts, plus assignment requirements. Your **activities** should call these functions and handle database persistence.

## Why We Use Temporal

Trellis coordinates long-running, stateful operations where reliability and clear audit trails matter (e.g., multi-step data workflows, vendor calls, human approvals). Temporal gives us:

- **Durability & fault tolerance.** Workflow state is persisted, so workers can crash or be redeployed without losing progress. Retries, backoffs, and timeouts are first-class—not bolted on.
- **Deterministic orchestration.** We encode the *control plane* (timers, signals, child workflows, compensation) once; Temporal replays history to guarantee consistent decisions across retries and restarts.
- **Idempotent side effects.** Activities are retried safely; we implement idempotency keys in our own DB to make external calls (payments, notifications, writes) safe to repeat.
- **Human-in-the-loop.** Signals and timers make manual review/approvals and SLAs natural, without custom schedulers or cron drift.
- **Observability by design.** The event history is a truthful source for debugging, auditing, and support. We can expose live status and recent errors without inventing bespoke tracking.

These capabilities map directly onto Trellis' needs: dependable automation across unreliable networks and third-party systems, clear visibility for operators, and safe recovery when anything fails.

### Why an "Order" workflow (instead of Trellis's per-service healthcare flows)

We picked an **Order → Payment → Shipping** model for the exercise because it's simple and self-contained while still exercising the core Temporal primitives we care about in real work:

- **Signals & timers:** Manual review before payment is a realistic human gate with a deadline.
- **Retries, timeouts, compensation:** Payments and dispatch are classic side-effects that must be idempotent and safely retried.
- **Child workflows & task-queue isolation:** Shipping runs on its own queue, showing how we scale teams/services independently.
- **End-to-end state & auditing:** Orders, payments, and shipping events provide a clean domain to persist to SQL and query live status.

An order domain avoids domain-specific baggage and lets you focus on orchestration quality—determinism, resilience, and observability—exactly what we evaluate for Trellis' production workflows.

---

## What to Build (Domain Scenario)

- Design your own **OrderWorkflow** and **ShippingWorkflow** (or equivalent), including signals, timers, retries, child workflows, and separate task queues.
- Implement **activities** that call the **functions** below.
- Use a **real local database** (SQL) for persistence. Include init/migration scripts.
- **Implement your own idempotency** logic for payment and other state‑changing operations.

### Parent Workflow: `OrderWorkflow`

- **Steps (activities):** `ReceiveOrder → ValidateOrder → (Timer: ManualReview) → ChargePayment → ShippingWorkflow`.
- **Signals:**
    - `CancelOrder` — cancels order before shipment.
    - `UpdateAddress` — updates shipping address prior to dispatch.
- **Timer:** Insert a delay between validation and payment (simulated manual review). Only goes onto the next part of the temporal workflow once a human manually approves the order, which then hits the ChargePayment activity.
- **Child Workflow:** After successful payment, start `ShippingWorkflow` on a **separate task queue**.
- **Cancellations/Failures:** Handle gracefully; propagate or compensate as appropriate.
- **Time Constraint:** The Entire Workflow Must Complete Within 15 seconds.

### Child Workflow: `ShippingWorkflow`

- **Activities:** `PreparePackage`, `DispatchCarrier`.
- **Parent Notification:** If dispatch fails, **signal back** to parent (e.g., `DispatchFailed(reason)`) and ask the Parent to retry .
- **Own task queue** (e.g., `"shipping-tq"`) to demonstrate queue isolation.

---

## Technical Expectations

- **Run everything locally** (no managed services):
    - Temporal dev server (Docker command above).
    - A **real database** you spin up locally (any flavor of SQL).
- **CLI or minimal API** that:
    1. launches Temporal server, database, and workers (via Docker Compose or scripts),
    2. **triggers** a workflow,
    3. **sends signals** (cancel, update address),
    4. **exposes an endpoint** (or CLI commands) to **inspect live state** (current step, retries, recent errors).
- **Tests:** unit and/or local integration tests using Temporal's Python testing tools.
- **Logging:** emit structured logs showing retries, cancellations, and state transitions.

---

## Functions to Implement (Call These From Your Activities)

The following Python **async functions** encapsulate business logic and failure simulation. Wire them into your activities. Each function includes a comment indicating where you should perform **database reads/writes**.

### Error/Timeout Simulation Helper (You cannot change this function, which must be called from all the Function Stubs)

```python
import asyncio, random

async def flaky_call() -> None:
    """Either raise an error or sleep long enough to trigger an activity timeout."""
    rand_num = random.random()
    if rand_num < 0.33:
        raise RuntimeError("Forced failure for testing")

    if rand_num < 0.67:
        await asyncio.sleep(300)  # Expect the activity layer to time out before this completes
```

### Function Stubs (With DB Notes — feel free to change the parameters, but they must call `flaky_call()`)

```python
from typing import Dict, Any

async def order_received(order_id: str) -> Dict[str, Any]:
    await flaky_call()
    # TODO: Implement DB write: insert new order record
    return {"order_id": order_id, "items": [{"sku": "ABC", "qty": 1}]}

async def order_validated(order: Dict[str, Any]) -> bool:
    await flaky_call()
    # TODO: Implement DB read/write: fetch order, update validation status
    if not order.get("items"):
        raise ValueError("No items to validate")
    return True

async def payment_charged(order: Dict[str, Any], payment_id: str, db) -> Dict[str, Any]:
    """Charge payment after simulating an error/timeout first.
    You must implement your own idempotency logic in the activity or here.
    """
    await flaky_call()
    # TODO: Implement DB read/write: check payment record, insert/update payment status
    amount = sum(i.get("qty", 1) for i in order.get("items", []))
    return {"status": "charged", "amount": amount}

async def order_shipped(order: Dict[str, Any]) -> str:
    await flaky_call()
    # TODO: Implement DB write: update order status to shipped
    return "Shipped"

async def package_prepared(order: Dict[str, Any]) -> str:
    await flaky_call()
    # TODO: Implement DB write: mark package prepared in DB
    return "Package ready"

async def carrier_dispatched(order: Dict[str, Any]) -> str:
    await flaky_call()
    # TODO: Implement DB write: record carrier dispatch status
    return "Dispatched"
```

> How to use in activities: Inside each Temporal activity, call the matching function above. Keep the activity small: parameter unpacking, await the function, return its result. Configure tight timeouts and retry policies on the activity to observe failures/timeouts caused by flaky_call().

---

## CLI/API Expectations

Provide a CLI or HTTP API that can:

- Start **Temporal server**, **database**, and **workers** (e.g., `docker compose up`).
- **Trigger** the workflow.
- **Send signals** (cancel, update address).
- **Inspect** live state: current step, retry counts, recent errors.

---

### CLI/API Example Endpoints

| Method & Path | Description |
| --- | --- |
| **POST** `/orders/{order_id}/start` | Starts `OrderWorkflow` with a provided `payment_id`. |
| **POST** `/orders/{order_id}/signals/cancel` | Sends the `CancelOrder` signal. |
| **GET** `/orders/{order_id}/status` | Queries `OrderWorkflow.status()` to retrieve current state. |

> You may implement these as FastAPI endpoints or simple CLI commands. Ensure logs clearly show retries, timeouts, and the current workflow step.

### Persistence (DB) Notes

- Use a real database and provide **migrations/init scripts**.
- **Some suggested tables (but not required):**
    - `orders(id, state, address_json, created_at, updated_at)`
    - `payments(payment_id PRIMARY KEY, order_id, status, amount, created_at)`
    - `events(id, order_id, type, payload_json, ts)` — for debugging/tracing
- **Idempotency:**
    - For payment, use a unique `payment_id` to upsert a row (`INSERT ... ON CONFLICT DO NOTHING`) and treat duplicates as already processed.
    - Record external side effects **after** they succeed; retries should be safe.

## Deliverables

- Public GitHub repo with source code.
- **README.md** with:
    - How to start Temporal server and database.
    - How to run workers and trigger workflow.
    - How to send signals and query/inspect state.
    - Schema/migrations and persistence rationale.
    - Tests and how to run them.

---

## Evaluation

- Correct use of Temporal primitives you design yourself.
- Clean, readable code and deterministic behavior.
- Proper persistence and **idempotent payment** logic you implement.
- Easy local spin‑up and clear observability (logs/queries).
- Does the entire workflow complete in 15 seconds?

---

## FAQ

**Where do I get the Temporal server?**

Use the open‑source dev server: `docker run --rm -d --name temporal -p 7233:7233 temporalio/auto-setup`.

**Do I need a real database?**

**Yes.** Use SQL locally; provide migrations and a connection recipe.

**How detailed should the CLI/API be?**

It should **run Temporal, the DB, your workers**, and expose an entrypoint to trigger workflows and **inspect progress/retries/errors**.

**Preferred Python version?** Any.

**Third‑party package limits?** None.

**Code style?** Clean/readable, nothing too fancy.

**Timeframe?** It shouldn't take more than a few hours, but feel free to spend as time as you need. Please return no later than 5 days of receiving the take home.

---

## Key Implementation Notes

### Critical Constraints
1. **15-second timeout**: The entire workflow must complete within 15 seconds
2. **Flaky function calls**: All function stubs must call `flaky_call()` which can fail or timeout
3. **Idempotency**: Payment operations must be idempotent using unique payment_id
4. **Real database**: Must use actual SQL database with migrations
5. **Local setup**: Everything must run locally (Temporal server, database, workers)

### Architecture Requirements
1. **Two workflows**: OrderWorkflow (parent) and ShippingWorkflow (child)
2. **Separate task queues**: Shipping workflow on its own queue
3. **Signals**: CancelOrder and UpdateAddress signals
4. **Timer**: Manual review timer between validation and payment
5. **Error handling**: Graceful handling of cancellations and failures
6. **Parent-child communication**: Shipping workflow can signal back to parent on failure

### Database Schema (Suggested)
- `orders(id, state, address_json, created_at, updated_at)`
- `payments(payment_id PRIMARY KEY, order_id, status, amount, created_at)`
- `events(id, order_id, type, payload_json, ts)`

### API/CLI Requirements
- Start infrastructure (Temporal, DB, workers)
- Trigger workflows
- Send signals
- Inspect live state and retry counts
- Clear logging of retries, timeouts, and state transitions

### Testing Requirements
- Unit and/or integration tests using Temporal's Python testing tools
- Structured logging for observability
- Easy local spin-up process
