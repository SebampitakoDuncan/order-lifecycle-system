# Order Lifecycle System

Temporal-based orchestration of an order lifecycle with a hard 15-second completion target, a PostgreSQL audit trail, a FastAPI REST API, and CLI utilities.

## Overview
- Parent workflow: receive → validate → manual review → charge → ship (child workflow).
- Child workflow (shipping) runs on its own task queue.
- Signals: cancel order, update address.
- Persistence: orders, payments (idempotent), and events in PostgreSQL.

## Prerequisites
- Docker and Docker Compose
- Python 3.8+

## Quick Start
1) Install dependencies
```bash
pip install -r requirements.txt
```

2) Start infrastructure (Temporal + UI + Postgres)
```bash
./scripts/start_infrastructure.sh
```

3) Start workers (order + shipping)
```bash
./scripts/start_workers.sh
```

4) Start API server
```bash
./scripts/start_api.sh
```

5) Verify health
```bash
curl http://localhost:8000/health
```

6) Monitor workflows
- Temporal UI: http://localhost:8080

## API (base: `http://localhost:8000`)
- Start Order
```bash
curl -X POST "http://localhost:8000/orders/{order_id}/start" \
  -H "Content-Type: application/json" \
  -d '{"initial_address": {"street": "123 Main St", "city": "Anytown", "state": "CA", "zip": "12345"}}'
```

- Get Status
```bash
curl "http://localhost:8000/orders/{order_id}/status"
```

- Cancel Order (signal)
```bash
curl -X POST "http://localhost:8000/orders/{order_id}/signals/cancel" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Customer request", "cancelled_by": "admin"}'
```

- Update Address (signal)
```bash
curl -X POST "http://localhost:8000/orders/{order_id}/signals/update-address" \
  -H "Content-Type: application/json" \
  -d '{"new_address": {"street": "456 Updated St", "city": "Updated City", "state": "NY", "zip": "54321"}, "updated_by": "admin"}'
```

- Get History
```bash
curl "http://localhost:8000/orders/{order_id}/history"
```

- List Orders
```bash
curl "http://localhost:8000/orders"
```

## CLI (optional)
```bash
# Start an order
python3 scripts/cli.py start ORDER_ID

# Get status
python3 scripts/cli.py status ORDER_ID

# Cancel
python3 scripts/cli.py cancel ORDER_ID --reason "Customer request" --cancelled-by admin

# Update address
python3 scripts/cli.py update-address ORDER_ID --address '{"street":"123 Main","city":"Any","state":"CA","zip":"12345"}' --updated-by admin

# List all
python3 scripts/cli.py list
```

## Configuration
Set via environment variables (see `env.example`):
- `DB_URL` (default recommended): `postgresql://postgres:password@localhost:5432/trellis_orderdb`
- `TEMPORAL_HOST` (default: `localhost`)
- `TEMPORAL_PORT` (default: `7233`)
- `TEMPORAL_NAMESPACE` (default: `default`)
- `ORDER_TASK_QUEUE` (default: `order-tq`)
- `SHIPPING_TASK_QUEUE` (default: `shipping-tq`)
- `WORKFLOW_TIMEOUT_SECONDS` (default: `15`)

## Testing
Run the available tests with pytest:
```bash
python3 -m pytest tests -v

# Specific files
python3 -m pytest tests/test_business_logic.py -v
python3 -m pytest tests/test_workflows.py -v
python3 -m pytest tests/test_parent_child_signals.py -v
python3 -m pytest tests/test_api.py -v
```

## Troubleshooting
- Infrastructure not running: `./scripts/start_infrastructure.sh`, then check `docker-compose ps`.
- Workers not processing: `./scripts/start_workers.sh` (view logs in terminal).
- API unavailable: ensure `./scripts/start_api.sh` is running, then `curl http://localhost:8000/health`.
- Validate timing: open Temporal UI (http://localhost:8080) and inspect event timestamps to confirm ≤ 15s.

## Project Structure
```
├── src/
│   ├── api/            # FastAPI application
│   ├── workers/        # Temporal workers (order + shipping)
│   ├── workflows/      # Temporal workflows + activities
│   ├── functions/      # Business logic + DB writes
│   └── database/       # DB pool + migrations
├── scripts/            # Infra, API, and worker scripts; CLI
├── tests/              # Pytest suites
└── docker-compose.yml  # Temporal + UI + Postgres
```

