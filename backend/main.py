"""
Data Analyst Copilot — FastAPI Backend
Main application entrypoint
"""
import os
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv(override=True)
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from routes import upload, profile, eda, chat, statistics, cleaning, export, sql_agent, suggestions, users

# Keep-alive: prevents Render free tier from spinning down after inactivity
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")  # Auto-set by Render in production
KEEPALIVE_INTERVAL_SECONDS = 10 * 60  # ping every 10 minutes

async def _keep_alive():
    """Periodically ping own health endpoint to prevent Render spin-down."""
    if not RENDER_URL:
        return  # Only runs in production (Render sets this env var automatically)
    url = f"{RENDER_URL}/api/health"
    logger_ka = logging.getLogger("keep_alive")
    logger_ka.info(f"Keep-alive task started — pinging {url} every {KEEPALIVE_INTERVAL_SECONDS // 60} min")
    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            await asyncio.sleep(KEEPALIVE_INTERVAL_SECONDS)
            try:
                resp = await client.get(url)
                logger_ka.debug(f"Keep-alive ping → {resp.status_code}")
            except Exception as e:
                logger_ka.warning(f"Keep-alive ping failed: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Ensure directories exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs/charts", exist_ok=True)
os.makedirs("outputs/reports", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    logger.info("🚀 Starting Data Analyst Copilot API...")
    
    # Firestore and Storage are initialized globally via auth_service.py
    logger.info("✅ Firebase services ready")

    # Start keep-alive background task (no-op locally, active on Render)
    keepalive_task = asyncio.create_task(_keep_alive())

    yield

    keepalive_task.cancel()
    logger.info("🛑 Shutting down...")


app = FastAPI(
    title="Data Analyst Copilot API",
    description="AI-powered data analytics platform with natural language querying, auto-EDA, and ML capabilities.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS
origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (chart outputs)
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# Routers
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(profile.router, prefix="/api/profile", tags=["Profile"])
app.include_router(eda.router, prefix="/api/eda", tags=["EDA"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(statistics.router, prefix="/api/statistics", tags=["Statistics"])
app.include_router(cleaning.router, prefix="/api/cleaning", tags=["Cleaning"])
app.include_router(export.router, prefix="/api/export", tags=["Export"])
app.include_router(sql_agent.router, prefix="/api/sql", tags=["SQL Agent"])
app.include_router(suggestions.router, prefix="/api/suggestions", tags=["Suggestions"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])


@app.get("/api/health", tags=["Health"])
@app.head("/api/health", tags=["Health"])
async def health_check():
    from services.data_service import get_store_memory_mb
    memory_info = {"dataframe_store_mb": round(get_store_memory_mb(), 1)}
    try:
        import psutil, os as _os
        proc = psutil.Process(_os.getpid())
        memory_info["process_rss_mb"] = round(proc.memory_info().rss / 1024 / 1024, 1)
    except Exception:
        pass
    return {"status": "healthy", "version": "1.0.0", "service": "Data Analyst Copilot", **memory_info}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
