import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.session import Session, SessionHandoff
from services.claude_service import generate_handoff

logger = logging.getLogger(__name__)


async def create_handoff(session_id: int, db: AsyncSession) -> SessionHandoff:
    """Generate and persist a handoff document for a session.

    Raises RuntimeError("handoff_exists") if one already exists.
    Raises ValueError if session not found.
    """
    existing = await db.scalar(
        select(SessionHandoff).where(SessionHandoff.session_id == session_id)
    )
    if existing is not None:
        raise RuntimeError("handoff_exists")

    session = await db.get(Session, session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")

    logger.info("Generating handoff for session %d", session_id)
    content = await generate_handoff(session.transcript, session.title)
    word_count = len(content.split())

    handoff = SessionHandoff(
        session_id=session_id,
        content=content,
        word_count=word_count,
    )
    db.add(handoff)
    await db.commit()
    await db.refresh(handoff)

    logger.info(
        "Handoff for session %d generated (%d words)", session_id, word_count
    )
    return handoff


async def get_handoff(session_id: int, db: AsyncSession) -> SessionHandoff | None:
    """Return cached handoff for a session, or None."""
    return await db.scalar(
        select(SessionHandoff).where(SessionHandoff.session_id == session_id)
    )
