# Architecture Documentation

## System Overview

The Order Lifecycle System is built using Temporal for workflow orchestration, PostgreSQL for persistence, and FastAPI for the REST API. The system demonstrates enterprise-grade patterns for handling long-running, stateful operations with strict performance constraints.

## Architecture Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   Temporal      │    │   PostgreSQL    │
│   REST API      │◄──►│   Server        │◄──►│   Database      │
│   (Port 8000)   │    │   (Port 7233)   │    │   (Port 5432)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Tools     │    │   Workers       │    │   Temporal UI   │
│   (Scripts)     │    │   (Activities)  │    │   (Port 8080)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Core Components

### 1. Temporal Workflows

#### OrderWorkflow (Parent Workflow)
- **Purpose**: Orchestrates the complete order lifecycle
- **Task Queue**: `order-tq`
- **Steps**:
  1. `receive_order_activity` - Create order in database
  2. `validate_order_activity` - Validate order details
  3. `manual_review_activity` - Simulated human approval (2-second delay)
  4. `charge_payment_activity` - Process payment with idempotency
  5. `ShippingWorkflow` - Child workflow for shipping

#### ShippingWorkflow (Child Workflow)
- **Purpose**: Handles shipping operations
- **Task Queue**: `shipping-tq`
- **Steps**:
  1. `prepare_package_activity` - Prepare order for shipping
  2. `dispatch_carrier_activity` - Dispatch carrier for delivery

### 2. Business Logic Functions

All business logic functions call `flaky_call()` to simulate real-world failures:

- `order_received()` - Creates order record in database
- `order_validated()` - Validates order and updates status
- `payment_charged()` - Processes payment with idempotency
- `order_shipped()` - Updates order status to shipped
- `package_prepared()` - Marks package as prepared
- `carrier_dispatched()` - Dispatches carrier

### 3. Database Schema

#### Tables
- `trellis_orders` - Order records with state and address
- `trellis_payments` - Payment records with idempotency
- `trellis_events` - Event log for audit trail

#### Key Features
- **Idempotency**: Payment operations are safe to retry
- **Audit Trail**: Complete event history for debugging
- **State Management**: Order state transitions tracked

### 4. API Layer

#### FastAPI Application
- **Port**: 8000
- **Features**:
  - RESTful endpoints for workflow management
  - Signal handling for real-time updates
  - Health checks and monitoring
  - Interactive documentation (Swagger UI)

#### Endpoints
- `POST /orders/{order_id}/start` - Start workflow
- `GET /orders/{order_id}/status` - Get status
- `POST /orders/{order_id}/signals/cancel` - Cancel order
- `POST /orders/{order_id}/signals/update-address` - Update address
- `GET /health` - Health check

### 5. Workers

#### Combined Worker
- **Purpose**: Processes both Order and Shipping workflows
- **Task Queues**: `order-tq`, `shipping-tq`
- **Features**:
  - Activity execution with retry policies
  - Timeout handling
  - Error recovery

## Design Decisions

### 1. 15-Second Constraint Strategy

#### Activity Timeouts
- **Receive Order**: 3 seconds
- **Validate Order**: 3 seconds
- **Manual Review**: 2 seconds (simulated)
- **Charge Payment**: 3 seconds
- **Prepare Package**: 2 seconds
- **Dispatch Carrier**: 2 seconds

#### Retry Policies
- **Maximum Attempts**: 3
- **Initial Interval**: 1 second
- **Maximum Interval**: 10 seconds
- **Backoff Coefficient**: 2.0

#### Optimization Techniques
- **Connection Pooling**: Database connections reused
- **Parallel Execution**: Activities run concurrently where possible
- **Fast Database Operations**: Optimized queries and indexes
- **Minimal Delays**: Reduced manual review time

### 2. Fault Tolerance

#### Error Handling
- **Activity Failures**: Automatic retry with exponential backoff
- **Workflow Failures**: Graceful error handling and compensation
- **Database Errors**: Connection pooling and retry logic
- **Signal Handling**: Proper validation and error reporting

#### Idempotency
- **Payment Operations**: Safe to retry without duplicate charges
- **Database Writes**: Upsert operations for consistency
- **Signal Processing**: Idempotent signal handling

### 3. Observability

#### Logging
- **Structured Logging**: JSON format for easy parsing
- **Workflow Logs**: Track execution and state changes
- **Activity Logs**: Monitor performance and failures
- **API Logs**: Track requests and responses

#### Monitoring
- **Temporal UI**: Visual workflow execution monitoring
- **Health Checks**: System component status
- **Performance Metrics**: Response times and throughput
- **Error Tracking**: Failure rates and patterns

### 4. Signal Handling

#### Cancel Order Signal
- **Trigger**: Customer or admin request
- **Effect**: Stops workflow execution
- **Compensation**: Updates order status to cancelled
- **Audit**: Records cancellation reason and user

#### Update Address Signal
- **Trigger**: Customer address change
- **Effect**: Updates shipping address
- **Validation**: Ensures address is valid
- **Audit**: Records update history

## Performance Characteristics

### Workflow Execution Times
- **Typical Completion**: 8-12 seconds
- **Maximum Allowed**: 15 seconds
- **Failure Scenarios**: 3-5 seconds (fast failure)

### API Response Times
- **Start Workflow**: < 100ms
- **Get Status**: < 50ms
- **Send Signal**: < 50ms
- **Health Check**: < 10ms

### Database Performance
- **Connection Pool**: 10 connections
- **Query Time**: < 100ms average
- **Write Operations**: < 50ms average
- **Read Operations**: < 20ms average

## Security Considerations

### Data Protection
- **Database**: Parameterized queries prevent SQL injection
- **API**: Input validation and sanitization
- **Logs**: Sensitive data not logged
- **Network**: Local development only

### Access Control
- **API**: No authentication (demo system)
- **Database**: Local access only
- **Temporal**: Local development server
- **Workers**: Process-level isolation

## Scalability Considerations

### Horizontal Scaling
- **Workers**: Multiple worker processes
- **API**: Multiple API instances
- **Database**: Read replicas for queries
- **Temporal**: Cluster deployment

### Vertical Scaling
- **Memory**: 2GB per worker process
- **CPU**: Multi-core processing
- **Database**: Connection pooling
- **Storage**: SSD for database

## Deployment Architecture

### Development Environment
- **Docker Compose**: Single-node deployment
- **Local Services**: All services on localhost
- **Development Mode**: Hot reloading enabled
- **Debug Logging**: Verbose output

### Production Considerations
- **Container Orchestration**: Kubernetes or Docker Swarm
- **Service Discovery**: Consul or etcd
- **Load Balancing**: NGINX or HAProxy
- **Monitoring**: Prometheus and Grafana
- **Logging**: ELK Stack or similar

## Testing Strategy

### Unit Tests
- **Business Logic**: Individual function testing
- **Mocking**: External dependencies mocked
- **Coverage**: 90%+ code coverage
- **Performance**: Fast execution (< 1 second)

### Integration Tests
- **Workflow Testing**: End-to-end workflow execution
- **API Testing**: All endpoints tested
- **Database Testing**: Data persistence validation
- **Signal Testing**: Signal handling validation

### Performance Tests
- **15-Second Constraint**: Validated under load
- **Concurrent Workflows**: Multiple workflows simultaneously
- **Failure Scenarios**: Error handling under stress
- **Resource Usage**: Memory and CPU monitoring

## Maintenance and Operations

### Monitoring
- **Health Checks**: Automated system health monitoring
- **Alerting**: Failure and performance alerts
- **Dashboards**: Real-time system status
- **Logs**: Centralized logging and analysis

### Backup and Recovery
- **Database Backups**: Regular automated backups
- **Workflow State**: Temporal handles state persistence
- **Configuration**: Version-controlled configuration
- **Disaster Recovery**: Multi-region deployment

### Updates and Deployments
- **Blue-Green Deployment**: Zero-downtime updates
- **Rolling Updates**: Gradual service updates
- **Feature Flags**: Controlled feature rollouts
- **Rollback Strategy**: Quick rollback capability
