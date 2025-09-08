-- Initial database schema for Order Lifecycle system
-- Following the suggested schema from requirements

-- Orders table
CREATE TABLE IF NOT EXISTS trellis_orders (
    id VARCHAR(255) PRIMARY KEY,
    state VARCHAR(50) NOT NULL DEFAULT 'pending',
    address_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Payments table with idempotency support
CREATE TABLE IF NOT EXISTS trellis_payments (
    payment_id VARCHAR(255) PRIMARY KEY,
    order_id VARCHAR(255) NOT NULL REFERENCES trellis_orders(id),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    amount DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Events table for debugging/tracing
CREATE TABLE IF NOT EXISTS trellis_events (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(255) NOT NULL REFERENCES trellis_orders(id),
    type VARCHAR(100) NOT NULL,
    payload_json JSONB,
    ts TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_trellis_orders_state ON trellis_orders(state);
CREATE INDEX IF NOT EXISTS idx_trellis_orders_created_at ON trellis_orders(created_at);
CREATE INDEX IF NOT EXISTS idx_trellis_payments_order_id ON trellis_payments(order_id);
CREATE INDEX IF NOT EXISTS idx_trellis_payments_status ON trellis_payments(status);
CREATE INDEX IF NOT EXISTS idx_trellis_events_order_id ON trellis_events(order_id);
CREATE INDEX IF NOT EXISTS idx_trellis_events_type ON trellis_events(type);
CREATE INDEX IF NOT EXISTS idx_trellis_events_ts ON trellis_events(ts);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_trellis_orders_updated_at 
    BEFORE UPDATE ON trellis_orders 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
