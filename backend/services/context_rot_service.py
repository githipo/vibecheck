import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.session import Session, SessionHealth
from services.claude_service import analyze_context_rot

logger = logging.getLogger(__name__)


async def compute_session_health(session_id: int, db: AsyncSession) -> SessionHealth:
    """Analyze a session transcript for context rot and persist the result.

    Raises ValueError if session not found or AI call fails.
    Raises RuntimeError if health already exists (caller should use get_session_health instead).
    """
    existing = await db.scalar(
        select(SessionHealth).where(SessionHealth.session_id == session_id)
    )
    if existing is not None:
        raise RuntimeError("health_exists")

    session = await db.get(Session, session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")

    logger.info("Analyzing context rot for session %d", session_id)
    data = await analyze_context_rot(session.transcript)

    health = SessionHealth(
        session_id=session_id,
        total_messages=int(data.get("total_messages", 0)),
        user_messages=int(data.get("user_messages", 0)),
        lazy_prompt_count=int(data.get("lazy_prompt_count", 0)),
        efficiency_score=float(data.get("efficiency_score", 100.0)),
        estimated_wasted_token_ratio=float(data.get("estimated_wasted_token_ratio", 0.0)),
        lazy_prompts=data.get("lazy_prompts", []),
        breakpoints=data.get("breakpoints", []),
        summary=data.get("summary", ""),
    )

    db.add(health)
    await db.commit()
    await db.refresh(health)

    logger.info(
        "Session %d health computed: efficiency=%.1f, lazy_prompts=%d",
        session_id,
        health.efficiency_score,
        health.lazy_prompt_count,
    )
    return health


async def get_session_health(session_id: int, db: AsyncSession) -> SessionHealth | None:
    """Return cached SessionHealth for a session, or None if not yet computed."""
    return await db.scalar(
        select(SessionHealth).where(SessionHealth.session_id == session_id)
    )
