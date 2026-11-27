"""
main.py — FastAPI application entry point for Mira Companion.

Run with:
    cd mira-companion/backend
    uvicorn app.main:app --reload --port 8000
"""
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the core/ directory (containing existing Python files) is importable
_core_path = str(Path(__file__).parent / "core")
if _core_path not in sys.path:
    sys.path.insert(0, _core_path)

from app.config import get_settings
from app.api import stone_routes, demand_routes, report_routes, lead_routes
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    On startup: inject environment variables so the existing core modules
    (demand_extract.py, particular_info.py, inventory_fetching.py) can read them
    via os.getenv() exactly as they do today.
    Also initialises the SQLite lead logger database.
    """
    settings = get_settings()
    if settings.groq_api_key:
        os.environ["GROQ_API_KEY"] = settings.groq_api_key
    if settings.mira_gems_api_key:
        os.environ["MIRA_GEMS_API_KEY"] = settings.mira_gems_api_key
    if settings.database_url:
        os.environ["DATABASE_URL"] = settings.database_url
    # Create Lead Logger DB tables (safe no-op if already created)
    init_db()
    yield


app = FastAPI(
    title="Mira Companion API",
    description="Internal diamond business assistant for Mira Gems",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()

# CORS — allow the Chrome extension and local dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_origin_regex=r"chrome-extension://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stone_routes.router, prefix="/api")
app.include_router(demand_routes.router, prefix="/api")
app.include_router(report_routes.router, prefix="/api")
app.include_router(lead_routes.router,   prefix="/api")


@app.get("/health", tags=["Health"])
async def health():
    """Health check — used by the Chrome extension to show connection status."""
    return {
        "status": "ok",
        "service": "Mira Companion API",
        "version": "1.0.0",
    }
