"""
NexusSearch - Main FastAPI Application
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.routes import search, auth, results
from app.models.database import engine, Base
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown events."""
    logger.info("NexusSearch API starting up...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized.")
    yield
    logger.info("NexusSearch API shutting down.")


app = FastAPI(
    title="NexusSearch OSINT API",
    description="Legal OSINT investigation platform — FastAPI backend",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — Allow the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include Routers ---
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(results.router, prefix="/api/results", tags=["Results"])


@app.get("/", tags=["Health"])
async def root():
    return {"status": "online", "service": "NexusSearch API v1.0"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}
