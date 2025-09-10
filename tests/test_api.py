import pytest
import httpx

from src.api.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    # Exercise the endpoint without relying on external services
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/health")
        assert res.status_code in (200, 503)

