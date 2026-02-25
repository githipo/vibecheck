import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.session import Quiz, Session
from schemas.session import QuizOut
from services.quiz_engine import create_quiz_for_session

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
            detail=f"No quiz found for session {session_id}",
        )
    return quiz


@router.post(
    "/sessions/{session_id}/quiz",
    response_model=QuizOut,
    status_code=status.HTTP_201_CREATED,
)
async def generate_quiz(
    session_id: int, db: AsyncSession = Depends(get_db)
) -> Quiz:
    """Generate a new quiz for the session by calling Claude."""
    session = await _get_session_or_404(session_id, db)

    if session.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session is already completed. Cannot regenerate quiz.",
        )

    try:
        quiz = await create_quiz_for_session(session, db)
    except ValueError as exc:
        logger.error("Quiz generation failed for session %d: %s", session_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Quiz generation failed: {exc}",
        ) from exc

    logger.info("Quiz id=%d generated for session id=%d", quiz.id, session_id)
    return quiz


@router.get("/sessions/{session_id}/quiz", response_model=QuizOut)
async def get_quiz(
    session_id: int, db: AsyncSession = Depends(get_db)
) -> Quiz:
    """Return the most recent quiz for the session."""
    await _get_session_or_404(session_id, db)
    return await _get_latest_quiz_or_404(session_id, db)
