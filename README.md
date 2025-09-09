# Order Lifecycle System

A Temporal-based order lifecycle orchestration system built for the Trellis Engineering take-home assignment. This system demonstrates enterprise-grade workflow orchestration with fault tolerance, observability, and strict performance constraints.

## 🎯 Project Overview

This system implements a complete order lifecycle using Temporal workflows, meeting all requirements from the Trellis Engineering take-home assignment:

- **15-Second Constraint**: All workflows complete within 15 seconds
- **Fault Tolerance**: Graceful handling of failures and retries
- **Signal Handling**: Real-time order cancellation and address updates
- **Database Persistence**: Complete audit trail in PostgreSQL
- **API & CLI**: Full REST API and command-line interface
- **Observability**: Comprehensive monitoring and logging

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.8+
- Git

### Setup Instructions

```bash
# Clone the repository
git clone https://github.com/SebampitakoDuncan/order-lifecycle-system.git
cd order-lifecycle-system

# Install Python dependencies
pip install -r requirements.txt
```

### 🧪 For Testing and Quick Demo

**If you want to test the system quickly, please read the [QUICK_START.md](QUICK_START.md) guide first!**

The quick start guide provides:
- 5-minute setup instructions
- Copy-paste API examples
- Troubleshooting for common issues
- Expected results and performance metrics

## 🏗️ Architecture

This system implements a complete order lifecycle using Temporal workflows, with the following components:

- **OrderWorkflow**: Main workflow orchestrating the complete order process
- **ShippingWorkflow**: Child workflow handling shipping operations
- **Business Logic Functions**: Core business operations with database integration
- **Temporal Workers**: Process workflows and activities on separate task queues
- **REST API**: FastAPI endpoints for workflow management
- **CLI Tools**: Command-line interface for system management
- **PostgreSQL Database**: Persistent storage for orders, payments, and events

## 🚀 Manual Setup (Alternative to Quick Start)

### 1. Start Infrastructure

```bash
# Start Temporal server, UI, and PostgreSQL database
./scripts/start_infrastructure.sh
```

This will start:
- Temporal server on `http://localhost:7233`
- Temporal UI on `http://localhost:8080`
- PostgreSQL database on `localhost:5432`

### 2. Start Workers

```bash
# Start both Order and Shipping workers
./scripts/start_workers.sh

# Or start workers individually
./scripts/start_order_worker.sh
./scripts/start_shipping_worker.sh
```

### 3. Start API Server

```bash
# Start FastAPI server
./scripts/start_api.sh
```

API will be available at:
- API: `http://localhost:8000`
- Documentation: `http://localhost:8000/docs`

## 📋 Workflow Overview

### OrderWorkflow

The main workflow orchestrates the complete order lifecycle:

1. **Receive Order** - Create new order in database
2. **Validate Order** - Validate order details and items
3. **Manual Review** - Simulated human approval (2-second delay)
4. **Charge Payment** - Process payment with idempotency
5. **Shipping Workflow** - Child workflow for shipping operations

### ShippingWorkflow

Child workflow handling shipping operations:

1. **Prepare Package** - Prepare order for shipping
2. **Dispatch Carrier** - Dispatch carrier for delivery

### Signals

- **CancelOrder**: Cancel order before shipping
- **UpdateAddress**: Update shipping address

### Constraints

- **15-second timeout**: Entire workflow must complete within 15 seconds
- **Idempotency**: Payment operations are idempotent and safe to retry
- **Fault tolerance**: Activities can fail and retry without losing state

## 🛠️ API Documentation

### Base URL
```
http://localhost:8000
```

### Interactive Documentation
Visit `http://localhost:8000/docs` for interactive API documentation with Swagger UI.

### Workflow Management

#### Start Order Workflow
```http
POST /orders/{order_id}/start
Content-Type: application/json

{
  "initial_address": {
    "street": "123 Main St",
    "city": "Anytown",
    "state": "CA",
    "zip": "12345"
  }
}
```

**Response:**
```json
{
  "workflow_id": "order-{order_id}",
  "order_id": "{order_id}",
  "status": "started",
  "message": "Order workflow started successfully"
}
```

#### Get Workflow Status
```http
GET /orders/{order_id}/status
```

**Response:**
```json
{
  "workflow_id": "order-{order_id}",
  "order_id": "{order_id}",
  "status": "running|completed|failed|cancelled",
  "result": {
    "order_id": "{order_id}",
    "status": "completed",
    "completed_steps": ["received", "validated", "reviewed", "payment_charged"],
    "payment_id": "payment-123"
  },
  "error": null,
  "completed_steps": ["received", "validated", "reviewed"],
  "created_at": "2025-09-08T05:12:39.402303Z",
  "updated_at": "2025-09-08T05:12:47.519177Z"
}
```

#### Get Workflow History
```http
GET /orders/{order_id}/history
```

#### List All Orders
```http
GET /orders
```

### Signals

#### Cancel Order
```http
POST /orders/{order_id}/signals/cancel
Content-Type: application/json

{
  "reason": "Customer request",
  "cancelled_by": "admin"
}
```

#### Update Address
```http
POST /orders/{order_id}/signals/update-address
Content-Type: application/json

{
  "new_address": {
    "street": "456 Updated St",
    "city": "Updated City",
    "state": "NY",
    "zip": "54321"
  },
  "updated_by": "admin"
}
```

### System

#### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy|unhealthy",
  "timestamp": "2025-09-08T15:14:29.824431",
  "temporal_connected": true,
  "database_connected": true,
  "workers_healthy": true
}
```

## 🖥️ CLI Tools

### Basic Commands

```bash
# Start an order workflow
python3 scripts/cli.py start ORDER_ID

# Get order status
python3 scripts/cli.py status ORDER_ID

# Cancel an order
python3 scripts/cli.py cancel ORDER_ID --reason "Customer request" --cancelled-by "admin"

# Update order address
python3 scripts/cli.py update-address ORDER_ID --address '{"street":"123 Main St","city":"Anytown","state":"CA","zip":"12345"}' --updated-by "admin"

# List all orders
python3 scripts/cli.py list

# Test workflow execution
python3 scripts/cli.py test ORDER_ID
```

## 🧪 Testing

The system includes a comprehensive test suite covering all components and scenarios. Tests are designed to validate functionality, performance, and reliability.

### 🚀 Quick Test Suite

**Run all tests with one command:**
```bash
python3 run_tests.py
```

This will execute:
- Unit tests for business logic
- Integration tests for workflows
- API endpoint tests
- Performance validation (15-second constraint)
- System integration tests

### 📋 Individual Test Categories

#### **Performance Tests**
```bash
# Validate 15-second constraint
python3 test_15_second_constraint.py

# Simple system validation
python3 test_simple_validation.py
```

#### **Unit Tests**
```bash
# Test business logic functions
python3 scripts/test_business_logic.py

# Test functions without flaky behavior
python3 scripts/test_functions_no_flaky.py

# Test functions with simple validation
python3 scripts/test_functions_simple.py
```

#### **Integration Tests**
```bash
# Test workflow execution
python3 scripts/test_workflows.py

# Test workflows with simple validation
python3 scripts/test_workflows_simple.py

# Test worker functionality
python3 scripts/test_workers.py
```

#### **API Tests**
```bash
# Test all API endpoints
python3 scripts/test_api.py

# Test system integration
python3 scripts/test_system.py

# Test Phase 5 functionality
python3 test_phase5.py
```

#### **Database Tests**
```bash
# Test database connection and schema
python3 debug_connection.py
```

### 🎯 Test Coverage

The test suite covers:

- ✅ **Business Logic**: All core functions with and without flaky behavior
- ✅ **Workflow Orchestration**: OrderWorkflow and ShippingWorkflow execution
- ✅ **API Endpoints**: All REST endpoints and error handling
- ✅ **Database Operations**: CRUD operations and data persistence
- ✅ **Performance**: 15-second constraint validation
- ✅ **Fault Tolerance**: Retry logic and error handling
- ✅ **Signal Handling**: Cancel and update-address signals
- ✅ **Child Workflows**: ShippingWorkflow execution and communication
- ✅ **Concurrent Processing**: Multiple workflow execution
- ✅ **System Integration**: End-to-end functionality

### 📊 Expected Test Results

**Performance Tests:**
- 15-second constraint: ✅ PASSED (8-14 seconds average)
- API response time: ✅ < 100ms
- Database operations: ✅ < 100ms

**Functional Tests:**
- Business logic: ✅ All functions working
- Workflow execution: ✅ Complete order lifecycle
- API endpoints: ✅ All endpoints functional
- Database persistence: ✅ Full audit trail

**Reliability Tests:**
- Fault tolerance: ✅ Graceful failure handling
- Retry logic: ✅ Automatic retry on failures
- Error handling: ✅ Proper error propagation

### 🔧 Test Configuration

Tests use the same infrastructure as the main system:
- **Database**: `trellis_orderdb` (same as production)
- **Temporal**: Local development server
- **API**: Local FastAPI instance
- **Workers**: Local worker processes

### 🐛 Troubleshooting Tests

**If tests fail:**
1. Ensure infrastructure is running: `./scripts/start_infrastructure.sh`
2. Start workers: `./scripts/start_workers.sh`
3. Check service health: `curl http://localhost:8000/health`
4. Review logs: `docker-compose logs`

**Common test issues:**
- **Connection errors**: Infrastructure not running
- **Timeout errors**: Workers not processing
- **Database errors**: PostgreSQL not accessible
- **Flaky test failures**: Expected behavior (retry logic working)

## 📊 Monitoring

### Temporal UI

Access the Temporal UI at `http://localhost:8080` to:
- View workflow executions
- Monitor activity performance
- Debug failed workflows
- Inspect workflow history

### Database

Connect to PostgreSQL to inspect data:

```bash
# Connect to database
docker exec -it postgres psql -U postgres -d trellis_orderdb

# View orders
SELECT * FROM trellis_orders;

# View payments
SELECT * FROM trellis_payments;

# View events
SELECT * FROM trellis_events ORDER BY ts DESC;
```

## 🏗️ Project Structure

```
├── src/
│   ├── api/                 # FastAPI application
│   ├── workers/             # Temporal workers
│   ├── workflows/           # Temporal workflows and activities
│   ├── functions/           # Business logic functions
│   ├── database/            # Database models and connection
│   └── config.py            # Configuration management
├── scripts/                 # Utility scripts
├── docker-compose.yml       # Infrastructure setup
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🔧 Configuration

Environment variables can be set in `.env` file:

```bash
# Database
DB_URL=postgresql://postgres:password@localhost:5432/trellis_orderdb

# Temporal
TEMPORAL_HOST=localhost
TEMPORAL_PORT=7233
TEMPORAL_NAMESPACE=default

# Task Queues
ORDER_TASK_QUEUE=order-tq
SHIPPING_TASK_QUEUE=shipping-tq

# Timeouts
ORDER_WORKFLOW_TIMEOUT_SECONDS=15
```

## 🚨 Error Handling

The system includes comprehensive error handling:

- **Activity Failures**: Automatic retry with exponential backoff
- **Workflow Failures**: Graceful error handling and compensation
- **Database Errors**: Connection pooling and retry logic
- **Signal Handling**: Proper signal validation and error reporting

## 📈 Performance

- **Concurrent Processing**: Workers can process multiple workflows simultaneously
- **Task Queue Isolation**: Order and Shipping workflows run on separate queues
- **Database Optimization**: Connection pooling and proper indexing
- **15-Second Constraint**: Workflows are designed to complete within the time limit

## 🔒 Security

- **Input Validation**: All API inputs are validated using Pydantic
- **Error Sanitization**: Sensitive information is not exposed in error messages
- **Database Security**: Parameterized queries prevent SQL injection

## 📝 Logging

Structured logging is implemented throughout the system:

- **Workflow Logs**: Track workflow execution and state changes
- **Activity Logs**: Monitor activity performance and failures
- **API Logs**: Track API requests and responses
- **Database Logs**: Monitor database operations

## 🔧 Troubleshooting

### Common Issues

#### 1. Infrastructure Not Starting
**Problem**: Docker containers fail to start
```bash
# Check Docker status
docker ps

# Restart infrastructure
./scripts/start_infrastructure.sh

# Check logs
docker-compose logs
```

#### 2. Workers Not Processing Workflows
**Problem**: Workflows start but don't complete
```bash
# Check if workers are running
ps aux | grep python

# Restart workers
./scripts/start_workers.sh

# Check worker logs
python3 -m src.workers.combined_worker
```

#### 3. API Connection Issues
**Problem**: API returns 503 Service Unavailable
```bash
# Check if API server is running
curl http://localhost:8000/health

# Restart API server
python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

#### 4. Database Connection Issues
**Problem**: Database connection errors
```bash
# Check PostgreSQL status
docker exec -it postgres psql -U postgres -d trellis_orderdb -c "SELECT 1;"

# Check database logs
docker logs postgres
```

#### 5. Workflow Timeout Issues
**Problem**: Workflows exceed 15-second constraint
```bash
# Check workflow performance
python3 test_15_second_constraint.py

# Monitor workflow execution
# Visit http://localhost:8080 (Temporal UI)
```

### Performance Issues

#### Workflow Taking Too Long
1. Check activity timeouts in workflow definitions
2. Verify database connection pooling
3. Monitor system resources (CPU, memory)
4. Check for network latency issues

#### High Memory Usage
1. Monitor worker processes
2. Check for memory leaks in activities
3. Restart workers periodically
4. Optimize database queries

### Debugging Workflows

#### Using Temporal UI
1. Visit `http://localhost:8080`
2. Navigate to "Workflows"
3. Search for your workflow ID
4. View execution history and events

#### Using CLI
```bash
# Get workflow status
python3 scripts/cli.py status ORDER_ID

# Get workflow history
python3 scripts/cli.py history ORDER_ID

# List all workflows
python3 scripts/cli.py list
```

#### Using API
```bash
# Get workflow status
curl http://localhost:8000/orders/ORDER_ID/status

# Get workflow history
curl http://localhost:8000/orders/ORDER_ID/history
```

### Log Analysis

#### Application Logs
```bash
# Check API logs
tail -f logs/api.log

# Check worker logs
tail -f logs/worker.log

# Check database logs
docker logs postgres
```

#### Temporal Logs
```bash
# Check Temporal server logs
docker logs temporal

# Check Temporal UI logs
docker logs temporal-ui
```

### Testing and Validation

#### Run All Tests
```bash
# Run comprehensive test suite
python3 run_tests.py

# Run specific test categories
python3 run_tests.py unit
python3 run_tests.py performance
python3 run_tests.py api
```

#### Validate 15-Second Constraint
```bash
# Run constraint validation
python3 test_15_second_constraint.py

# Run simple validation
python3 test_simple_validation.py
```

### Environment Issues

#### Python Dependencies
```bash
# Install dependencies
pip install -r requirements.txt

# Check Python version
python3 --version  # Should be 3.8+

# Check installed packages
pip list
```

#### Docker Issues
```bash
# Check Docker version
docker --version

# Check Docker Compose version
docker-compose --version

# Restart Docker service (if needed)
sudo systemctl restart docker
```

## 📊 Performance Monitoring

### Key Metrics
- **Workflow Completion Time**: Should be ≤ 15 seconds
- **API Response Time**: Should be ≤ 1 second
- **Database Query Time**: Should be ≤ 100ms
- **Worker CPU Usage**: Should be ≤ 80%
- **Memory Usage**: Should be ≤ 2GB per worker

### Monitoring Tools
- **Temporal UI**: `http://localhost:8080`
- **API Health**: `http://localhost:8000/health`
- **Database**: Connect to `localhost:5432`
- **System Resources**: Use `htop` or `top`


