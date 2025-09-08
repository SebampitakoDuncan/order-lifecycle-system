"""
Configuration management for the Order Lifecycle system.
Handles environment variables and application settings.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration."""
    
    # Database configuration
    DB_URL: str = os.getenv('DB_URL', 'postgresql://postgres:password@localhost:5432/orderdb')
    
    # Temporal configuration
    TEMPORAL_HOST: str = os.getenv('TEMPORAL_HOST', 'localhost')
    TEMPORAL_PORT: int = int(os.getenv('TEMPORAL_PORT', '7233'))
    TEMPORAL_NAMESPACE: str = os.getenv('TEMPORAL_NAMESPACE', 'default')
    TEMPORAL_UI_URL: str = os.getenv('TEMPORAL_UI_URL', 'http://localhost:8080')
    
    # Task queue names
    ORDER_TASK_QUEUE: str = os.getenv('ORDER_TASK_QUEUE', 'order-tq')
    SHIPPING_TASK_QUEUE: str = os.getenv('SHIPPING_TASK_QUEUE', 'shipping-tq')
    
    # Workflow configuration
    WORKFLOW_TIMEOUT_SECONDS: int = int(os.getenv('WORKFLOW_TIMEOUT_SECONDS', '15'))
    ACTIVITY_TIMEOUT_SECONDS: int = int(os.getenv('ACTIVITY_TIMEOUT_SECONDS', '3'))
    
    # API configuration
    API_HOST: str = os.getenv('API_HOST', '0.0.0.0')
    API_PORT: int = int(os.getenv('API_PORT', '8000'))
    
    # Logging configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    @property
    def temporal_url(self) -> str:
        """Get the full Temporal server URL."""
        return f"{self.TEMPORAL_HOST}:{self.TEMPORAL_PORT}"

# Global configuration instance
config = Config()
