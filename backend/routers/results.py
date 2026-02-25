import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.session import Attempt, Quiz, Session
from schemas.session import AttemptCreate, AttemptOut
from services.quiz_engine import submit_attempt

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_session_or_404(session_id: int, db: AsyncSession) -> Session:
    session = await db.get(Session, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    return session


async def _get_latest_quiz_or_404(session_id: int, db: AsyncSession) -> Quiz:
    result = await db.execute(
        select(Quiz)
        .where(Quiz.session_id == session_id)
        .order_by(Quiz.created_at.desc())
        .limit(1)
    )
    quiz = result.scalar_one_or_none()
    if quiz is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No quiz found for session {session_id}. Generate one first.",
        )
    return quiz


@router.post(
    "/sessions/{session_id}/attempt",
    response_model=AttemptOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_attempt(
    session_id: int,
    payload: AttemptCreate,
    db: AsyncSession = Depends(get_db),
) -> Attempt:
    """Submit answers for a session's quiz and receive Claude's evaluation."""
    session = await _get_session_or_404(session_id, db)
    quiz = await _get_latest_quiz_or_404(session_id, db)

    answers = [a.model_dump() for a in payload.answers]

    try:
        attempt = await submit_attempt(session, quiz, answers, db)
    except ValueError as exc:
        logger.error("Attempt evaluation failed for session %d: %s", session_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Answer evaluation failed: {exc}",
        ) from exc

    logger.info(
        "Attempt id=%d recorded for session id=%d; score=%.1f",
        attempt.id,
        session_id,
        attempt.score,
    )
    return attempt


@router.get("/sessions/{session_id}/results", response_model=AttemptOut)
async def get_results(
    session_id: int, db: AsyncSession = Depends(get_db)
) -> Attempt:
    """Return the most recent attempt results for a session."""
    await _get_session_or_404(session_id, db)

    result = await db.execute(
        select(Attempt)
        .where(Attempt.session_id == session_id)
        .order_by(Attempt.created_at.desc())
        .limit(1)
    )
    attempt = result.scalar_one_or_none()
    if attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No attempt found for session {session_id}",
        )
    return attempt
