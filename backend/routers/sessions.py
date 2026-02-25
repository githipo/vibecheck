import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.session import Session
from schemas.session import SessionCreate, SessionDetail, SessionOut

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreate, db: AsyncSession = Depends(get_db)
) -> Session:
    """Create a new session from a pasted or uploaded transcript."""
    session = Session(
        title=payload.title,
        transcript=payload.transcript,
        source_type=payload.source_type,
        status="pending_quiz",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    logger.info("Created session id=%d title=%r", session.id, session.title)
    return session


@router.get("", response_model=list[SessionOut])
async def list_sessions(db: AsyncSession = Depends(get_db)) -> list[Session]:
    """Return all sessions, most recent first."""
    result = await db.execute(
        select(Session).order_by(Session.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: int, db: AsyncSession = Depends(get_db)
) -> Session:
    """Return a single session including its full transcript."""
    session = await db.get(Session, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: int, db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a session and all related quizzes and attempts."""
    session = await db.get(Session, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    await db.delete(session)
    await db.commit()
    logger.info("Deleted session id=%d", session_id)
