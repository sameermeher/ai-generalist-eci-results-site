"""Integration tests for FastAPI endpoints using httpx AsyncClient."""

import pytest
from httpx import AsyncClient, ASGITransport

from api.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


# ---------------------------------------------------------------------------
# Elections
# ---------------------------------------------------------------------------

async def test_list_elections(client: AsyncClient):
    resp = await client.get("/elections/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------

async def test_list_states(client: AsyncClient):
    resp = await client.get("/states/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_get_state_unknown_code_returns_404(client: AsyncClient):
    resp = await client.get("/states/ZZZ")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

async def test_state_summaries(client: AsyncClient):
    resp = await client.get("/analytics/state-summaries")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_top_margins(client: AsyncClient):
    resp = await client.get("/analytics/top-margins")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_closest_contests(client: AsyncClient):
    resp = await client.get("/analytics/closest-contests")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# Parties
# ---------------------------------------------------------------------------

async def test_list_parties(client: AsyncClient):
    resp = await client.get("/parties/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
