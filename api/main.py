"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routers import analytics, constituencies, elections, parties, states
from config import settings
from db.session import async_engine

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting ECI Election Results API (env=%s)", settings.app_env)
    yield
    await async_engine.dispose()
    log.info("Async engine disposed.")


app = FastAPI(
    title="ECI Election Results API",
    description="Election Results Analytics Portal — May 2026",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow Streamlit dashboard origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production via env
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Exception handlers
# ------------------------------------------------------------------


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled exception: %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ------------------------------------------------------------------
# Routers
# ------------------------------------------------------------------

app.include_router(elections.router)
app.include_router(states.router)
app.include_router(constituencies.router)
app.include_router(parties.router)
app.include_router(analytics.router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "env": settings.app_env}
