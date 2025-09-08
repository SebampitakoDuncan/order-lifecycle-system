"""
SQLAlchemy models for the Order Lifecycle system.
Defines the database schema for orders, payments, and events.
"""
from sqlalchemy import Column, String, DateTime, Numeric, Integer, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, Any, Optional

Base = declarative_base()

class Order(Base):
    """Order model representing an order in the system."""
    __tablename__ = 'orders'
    
    id = Column(String(255), primary_key=True)
    state = Column(String(50), nullable=False, default='pending')
    address_json = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert order to dictionary."""
        return {
            'id': self.id,
            'state': self.state,
            'address_json': self.address_json,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Payment(Base):
    """Payment model with idempotency support."""
    __tablename__ = 'payments'
    
    payment_id = Column(String(255), primary_key=True)
    order_id = Column(String(255), ForeignKey('orders.id'), nullable=False)
    status = Column(String(50), nullable=False, default='pending')
    amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert payment to dictionary."""
        return {
            'payment_id': self.payment_id,
            'order_id': self.order_id,
            'status': self.status,
            'amount': float(self.amount) if self.amount else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Event(Base):
    """Event model for debugging and tracing."""
    __tablename__ = 'events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(255), ForeignKey('orders.id'), nullable=False)
    type = Column(String(100), nullable=False)
    payload_json = Column(JSONB)
    ts = Column(DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'type': self.type,
            'payload_json': self.payload_json,
            'ts': self.ts.isoformat() if self.ts else None
        }
