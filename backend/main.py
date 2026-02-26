import logging
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    from db import init_db

    logger.info("Starting up — initializing database")
    await init_db()
    logger.info("Database ready")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="VibeCheck API",
    version="0.1.0",
    description="Learning-verification companion for AI-assisted workflows",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173")
cors_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
from routers.sessions import router as sessions_router  # noqa: E402
from routers.quiz import router as quiz_router  # noqa: E402
from routers.results import router as results_router  # noqa: E402
from routers.insights import router as insights_router  # noqa: E402
from routers.analytics import router as analytics_router  # noqa: E402
from routers.codebase import router as codebase_router  # noqa: E402
from routers.multi_repo import router as multi_repo_router  # noqa: E402

app.include_router(sessions_router, prefix="/api/sessions", tags=["sessions"])

# Quiz, results, insights, analytics, codebase, and multi_repo routers handle
# their own full paths so they are mounted at /api with no additional prefix.
app.include_router(quiz_router, prefix="/api", tags=["quiz"])
app.include_router(results_router, prefix="/api", tags=["results"])
app.include_router(insights_router, prefix="/api", tags=["insights"])
app.include_router(analytics_router, prefix="/api", tags=["analytics"])
app.include_router(codebase_router, prefix="/api", tags=["codebase"])
app.include_router(multi_repo_router, prefix="/api", tags=["multi-repo"])


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
