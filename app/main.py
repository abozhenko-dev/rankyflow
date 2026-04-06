"""
SEO Competitor Tracker — FastAPI Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.core.config import settings
from app.api.v1 import api_router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown events."""
    logger.info("Starting SEO Competitor Tracker", env=settings.app_env)

    # Init Sentry in production
    if settings.sentry_dsn and settings.is_production:
        import sentry_sdk
        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.2)

    yield

    logger.info("Shutting down")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/debug/ip")
async def debug_ip():
    """Temporary endpoint to check outbound IP."""
    import httpx
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get("https://api.ipify.org?format=json")
        return r.json()


@app.post("/debug/migrate")
async def debug_migrate():
    """Temporary: add missing columns to keywords table."""
    from sqlalchemy import text
    from app.core.database import engine
    results = []
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE keywords ADD COLUMN IF NOT EXISTS latest_position INTEGER"))
            results.append("latest_position: ok")
        except Exception as e:
            results.append(f"latest_position: {e}")
        try:
            await conn.execute(text("ALTER TABLE keywords ADD COLUMN IF NOT EXISTS position_change INTEGER"))
            results.append("position_change: ok")
        except Exception as e:
            results.append(f"position_change: {e}")
        # Check columns
        try:
            r = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='keywords'"))
            cols = [row[0] for row in r.fetchall()]
            results.append(f"columns: {cols}")
        except Exception as e:
            results.append(f"cols_check: {e}")
    return {"results": results}


@app.get("/debug/test-dataforseo")
async def debug_test_dataforseo():
    """Test DataForSEO API directly."""
    import httpx, base64
    from app.core.config import settings
    creds = f"{settings.dataforseo_login}:{settings.dataforseo_password}"
    auth = base64.b64encode(creds.encode()).decode()
    payload = [{"keyword": "seo tools", "location_code": 2840, "language_code": "en", "device": "desktop", "depth": 10}]
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.dataforseo.com/v3/serp/google/organic/live/regular",
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
            json=payload,
        )
        data = r.json()
        status = data.get("status_code")
        tasks = data.get("tasks", [])
        task_status = tasks[0].get("status_code") if tasks else None
        task_msg = tasks[0].get("status_message") if tasks else None
        # Get top 5 organic
        top5 = []
        if tasks and tasks[0].get("status_code") == 20000:
            for rs in tasks[0].get("result", []):
                for item in rs.get("items", []):
                    if item.get("type") == "organic" and len(top5) < 5:
                        top5.append({"pos": item.get("rank_group"), "domain": item.get("domain")})
        return {"api_status": status, "task_status": task_status, "task_msg": task_msg, "top5": top5}
