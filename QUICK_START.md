# Order Lifecycle System - Quick Start Guide

A Temporal-based order workflow system that completes within 15 seconds. Ready to run in 5 minutes!

## 🚀 Quick Setup (5 minutes)

### Prerequisites
- Docker & Docker Compose
- Python 3.8+
- Git

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd temp14
pip install -r requirements.txt
```

### 2. Start Infrastructure
```bash
# Start Temporal server, UI, and PostgreSQL (handles conflicts automatically)
./scripts/start_infrastructure.sh

# Wait for services to fully initialize (60 seconds), then start workers
./scripts/start_workers.sh

# Start API server (in new terminal)
python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

**Or use the automated setup:**
```bash
# One-command setup (recommended for first-time users)
./setup.sh
```

### 3. Verify Setup
```bash
# Check health
curl http://localhost:8000/health

# Should return: {"status":"healthy","database_connected":true,...}
```

## 🧪 Test the System

### Quick API Test
```bash
# Start an order workflow
curl -X POST "http://localhost:8000/orders/test-order-001/start" \
  -H "Content-Type: application/json" \
  -d '{"initial_address": {"street": "123 Main St", "city": "Anytown", "state": "CA", "zip": "12345"}}'

# Check status
curl http://localhost:8000/orders/test-order-001/status

# Cancel the order
curl -X POST "http://localhost:8000/orders/test-order-001/signals/cancel" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Test cancellation", "cancelled_by": "user"}'

# List all orders
curl http://localhost:8000/orders
```

### Validate 15-Second Constraint
```bash
# Run performance test
python3 test_15_second_constraint.py

# Should show: "🎉 ALL TESTS PASSED! 15-second constraint is satisfied."
```

## 📋 Copy-Paste Examples

### 1. Start Order Workflow
```bash
curl -X POST "http://localhost:8000/orders/my-order-123/start" \
  -H "Content-Type: application/json" \
  -d '{
    "initial_address": {
      "street": "456 Oak Avenue",
      "city": "Springfield",
      "state": "IL",
      "zip": "62701"
    }
  }'
```

### 2. Get Order Status
```bash
curl http://localhost:8000/orders/my-order-123/status
```

### 3. Update Shipping Address
```bash
curl -X POST "http://localhost:8000/orders/my-order-123/signals/update-address" \
  -H "Content-Type: application/json" \
  -d '{
    "new_address": {
      "street": "789 Pine Street",
      "city": "Chicago",
      "state": "IL",
      "zip": "60601"
    },
    "updated_by": "customer"
  }'
```

### 4. Cancel Order
```bash
curl -X POST "http://localhost:8000/orders/my-order-123/signals/cancel" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Customer changed mind",
    "cancelled_by": "admin"
  }'
```

### 5. Get Workflow History
```bash
curl http://localhost:8000/orders/my-order-123/history
```

### 6. List All Orders
```bash
curl http://localhost:8000/orders
```

## 🖥️ Web Interfaces

- **API Documentation**: http://localhost:8000/docs (Interactive Swagger UI)
- **Temporal UI**: http://localhost:8080 (Workflow monitoring)
- **Health Check**: http://localhost:8000/health

## 🐛 Troubleshooting

### Services Not Starting?
```bash
# Check Docker status
docker ps

# Clean restart (handles container name conflicts)
docker-compose down -v
./scripts/start_infrastructure.sh
```

### Container Name Conflicts?
```bash
# If you get "container name already in use" errors:
docker-compose down -v
docker system prune -f
./scripts/start_infrastructure.sh
```

### API Not Responding?
```bash
# Check if API is running
curl http://localhost:8000/health

# Restart API server
python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### Workflows Not Processing?
```bash
# Check workers
ps aux | grep python

# Restart workers
./scripts/start_workers.sh
```

## 📊 Expected Results

### Successful Order Flow
1. **Start**: Returns `{"status": "started", "workflow_id": "order-..."}`
2. **Status**: Shows `"status": "running"` then `"completed"` or `"failed"`
3. **Cancel**: Returns `{"status": "cancelled", "message": "Cancel signal sent successfully"}`

### Performance
- **Workflow completion**: 8-14 seconds (within 15-second constraint)
- **API response**: < 100ms
- **Success rate**: 100% for valid requests

## 🎯 Key Features Demonstrated

- ✅ **15-Second Constraint**: All workflows complete within time limit
- ✅ **Fault Tolerance**: Handles failures gracefully with retries
- ✅ **Real-time Signals**: Cancel orders and update addresses instantly
- ✅ **Database Persistence**: Complete audit trail in PostgreSQL
- ✅ **API & CLI**: Full REST API with interactive documentation
- ✅ **Monitoring**: Visual workflow tracking in Temporal UI

## 📁 Project Structure
```
├── src/
│   ├── api/          # FastAPI REST endpoints
│   ├── workflows/    # Temporal workflows
│   ├── workers/      # Activity workers
│   └── database/     # PostgreSQL models
├── scripts/          # Setup and utility scripts
├── tests/           # Test suites
└── docker-compose.yml # Infrastructure setup
```

## 🚀 Next Steps

1. **Explore the API**: Visit http://localhost:8000/docs
2. **Monitor Workflows**: Check http://localhost:8080
3. **Run Tests**: `python3 test_15_second_constraint.py`
4. **Read Full Docs**: See `README.md` for detailed documentation

---


