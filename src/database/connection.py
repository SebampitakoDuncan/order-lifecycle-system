"""
Database connection management using asyncpg.
Handles connection pooling and provides database operations.
"""
import os
import asyncio
import asyncpg
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and provides async database operations."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.db_url = os.getenv('DB_URL', 'postgresql://postgres:password@localhost:5432/trellis_orderdb')
    
    async def initialize(self):
        """Initialize the database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def close(self):
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def execute(self, query: str, *args) -> str:
        """Execute a query that doesn't return results."""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Fetch a single row."""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        """Fetch multiple rows."""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchval(self, query: str, *args) -> Any:
        """Fetch a single value."""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

# Global database manager instance
db_manager = DatabaseManager()

async def get_db() -> DatabaseManager:
    """Get the database manager instance."""
    if not db_manager.pool:
        await db_manager.initialize()
    return db_manager
