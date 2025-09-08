# Trellis Engineering Takehome - Implementation Plan

## Overview
This plan addresses all requirements from REQUIREMENTS.md to build a Temporal-based Order Lifecycle system with PostgreSQL persistence, proper error handling, and a 15-second completion constraint.

## Project Structure
```
temp14/
├── docker-compose.yml          # Infrastructure setup
├── requirements.txt            # Python dependencies
├── README.md                  # Setup and usage instructions
├── src/
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py      # DB connection management
│   │   ├── models.py          # SQLAlchemy models
│   │   └── migrations/        # Database migrations
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── order_workflow.py  # OrderWorkflow implementation
│   │   └── shipping_workflow.py # ShippingWorkflow implementation
│   ├── activities/
│   │   ├── __init__.py
│   │   ├── order_activities.py # Order-related activities
│   │   └── shipping_activities.py # Shipping-related activities
│   ├── functions/
│   │   ├── __init__.py
│   │   └── business_logic.py  # Function stubs with DB integration
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI application
│   │   └── routes.py         # API endpoints
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── order_worker.py   # Order workflow worker
│   │   └── shipping_worker.py # Shipping workflow worker
│   └── utils/
│       ├── __init__.py
│       ├── logging.py        # Structured logging setup
│       └── temporal_client.py # Temporal client configuration
├── tests/
│   ├── __init__.py
│   ├── test_workflows.py     # Workflow tests
│   ├── test_activities.py    # Activity tests
│   └── test_integration.py   # Integration tests
└── scripts/
    ├── start_infrastructure.sh # Start Temporal + DB
    ├── run_workers.sh         # Start workers
    └── test_workflow.py       # Manual workflow testing
```

## Implementation Phases

### Phase 1: Infrastructure Setup (30 minutes)
**Goal**: Set up local development environment with Temporal server and PostgreSQL

**Tasks**:
1. **Docker Compose Setup**
   - Temporal dev server container
   - PostgreSQL database container
   - Network configuration
   - Volume mounts for persistence

2. **Database Schema**
   - Create migration scripts for:
     - `orders` table: `(id, state, address_json, created_at, updated_at)`
     - `payments` table: `(payment_id PRIMARY KEY, order_id, status, amount, created_at)`
     - `events` table: `(id, order_id, type, payload_json, ts)`
   - Database connection management with asyncpg
   - Connection pooling configuration

3. **Project Dependencies**
   - Temporal Python SDK
   - FastAPI for API endpoints
   - asyncpg for PostgreSQL
   - SQLAlchemy for ORM
   - Pydantic for data validation
   - pytest for testing

### Phase 2: Core Business Logic (45 minutes)
**Goal**: Implement the function stubs with proper database integration

**Tasks**:
1. **Function Stubs Implementation**
   - Implement all 6 function stubs from requirements
   - Add proper database read/write operations
   - Implement idempotency logic for payments
   - Error handling and logging

2. **Database Models**
   - SQLAlchemy models for orders, payments, events
   - Async database operations
   - Proper indexing for performance

3. **Configuration Management**
   - Environment variables for database URLs
   - Temporal server configuration
   - Logging configuration

### Phase 3: Temporal Workflows (60 minutes)
**Goal**: Implement OrderWorkflow and ShippingWorkflow with all required features

**Tasks**:
1. **OrderWorkflow Implementation**
   - Activity sequence: ReceiveOrder → ValidateOrder → (Timer: ManualReview) → ChargePayment → ShippingWorkflow
   - Signal handlers: CancelOrder, UpdateAddress
   - Manual review timer (simulated human approval)
   - Child workflow execution on separate task queue
   - 15-second timeout constraint
   - Proper error handling and compensation

2. **ShippingWorkflow Implementation**
   - Activities: PreparePackage, DispatchCarrier
   - Parent notification on failure
   - Separate task queue (`shipping-tq`)
   - Signal back to parent on dispatch failure

3. **Activity Implementations**
   - Order activities with proper timeouts and retry policies
   - Shipping activities with error handling
   - Database integration in each activity
   - Structured logging for observability

### Phase 4: Workers and Task Queues (30 minutes)
**Goal**: Set up Temporal workers for both workflows

**Tasks**:
1. **Order Worker**
   - Register OrderWorkflow and order activities
   - Configure task queue (`order-tq`)
   - Proper worker lifecycle management

2. **Shipping Worker**
   - Register ShippingWorkflow and shipping activities
   - Configure separate task queue (`shipping-tq`)
   - Worker configuration and startup

3. **Worker Management**
   - Graceful shutdown handling
   - Health checks
   - Logging and monitoring

### Phase 5: API and CLI (45 minutes)
**Goal**: Create FastAPI endpoints and CLI tools for workflow management

**Tasks**:
1. **FastAPI Application**
   - POST `/orders/{order_id}/start` - Start OrderWorkflow
   - POST `/orders/{order_id}/signals/cancel` - Send CancelOrder signal
   - POST `/orders/{order_id}/signals/update-address` - Send UpdateAddress signal
   - GET `/orders/{order_id}/status` - Get workflow status
   - GET `/orders/{order_id}/history` - Get workflow history
   - GET `/health` - Health check endpoint

2. **CLI Tools**
   - Script to start infrastructure (Temporal + DB)
   - Script to run workers
   - Script to trigger test workflows
   - Script to send signals manually

3. **State Inspection**
   - Workflow status querying
   - Retry count tracking
   - Error history display
   - Real-time status updates

### Phase 6: Testing and Validation (30 minutes)
**Goal**: Implement comprehensive tests and validate 15-second constraint

**Tasks**:
1. **Unit Tests**
   - Test individual activities
   - Test function stubs with database operations
   - Test idempotency logic

2. **Integration Tests**
   - End-to-end workflow testing
   - Signal handling tests
   - Error scenario testing
   - 15-second timeout validation

3. **Performance Testing**
   - Measure workflow completion times
   - Test under various failure scenarios
   - Validate retry behavior
   - Ensure 15-second constraint is met

### Phase 7: Documentation and Finalization (15 minutes)
**Goal**: Create comprehensive documentation and finalize the solution

**Tasks**:
1. **README.md**
   - Setup instructions
   - Usage examples
   - API documentation
   - Troubleshooting guide

2. **Code Documentation**
   - Inline comments
   - Docstrings for all functions
   - Architecture decisions
   - Database schema rationale

3. **Final Validation**
   - Run complete test suite
   - Validate all requirements are met
   - Performance testing
   - Documentation review

## Critical Implementation Details

### 15-Second Constraint Strategy
- **Activity Timeouts**: Set tight timeouts (2-3 seconds) on activities
- **Retry Policies**: Aggressive retry with exponential backoff
- **Timer Optimization**: Minimal manual review timer (1-2 seconds)
- **Parallel Execution**: Where possible, run activities in parallel
- **Fast Database Operations**: Optimized queries and connection pooling

### Idempotency Implementation
- **Payment Idempotency**: Use `payment_id` as unique key with `INSERT ... ON CONFLICT DO NOTHING`
- **Order State Management**: Track state transitions in database
- **Event Logging**: Record all state changes for audit trail
- **Retry Safety**: All external operations are idempotent

### Error Handling Strategy
- **Activity Level**: Catch and handle `flaky_call()` failures
- **Workflow Level**: Implement compensation logic
- **Signal Handling**: Graceful cancellation and address updates
- **Parent-Child Communication**: Proper error propagation

### Observability Features
- **Structured Logging**: JSON logs with correlation IDs
- **Workflow History**: Complete audit trail
- **Metrics**: Retry counts, completion times, error rates
- **Health Checks**: System status monitoring

## Success Criteria
1. ✅ All workflows complete within 15 seconds
2. ✅ Proper use of Temporal primitives (signals, timers, child workflows)
3. ✅ Real database with migrations and idempotency
4. ✅ FastAPI endpoints for workflow management
5. ✅ Comprehensive test coverage
6. ✅ Clear documentation and setup instructions
7. ✅ Structured logging and observability
8. ✅ Graceful error handling and retries

## Risk Mitigation
- **15-Second Constraint**: Start with aggressive timeouts and optimize iteratively
- **Flaky Function Calls**: Implement robust retry policies and error handling
- **Database Performance**: Use connection pooling and optimized queries
- **Complex Workflow Logic**: Break down into smaller, testable components
- **Integration Issues**: Test each component in isolation first

This plan ensures all requirements from REQUIREMENTS.md are met while maintaining clean, readable code and proper error handling throughout the system.
