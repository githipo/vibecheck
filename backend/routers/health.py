import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from schemas.session import SessionHealthOut
from services.context_rot_service import compute_session_health, get_session_health

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/sessions/{session_id}/health", response_model=SessionHealthOut, status_code=201)
async def analyze_health(
    session_id: int,
    db: AsyncSession = Depends(get_db),
) -> SessionHealthOut:
    """Analyze a session transcript for context rot patterns.

    Returns 409 if health report already exists (use GET to retrieve it).
    """
    try:
        health = await compute_session_health(session_id, db)
    except RuntimeError as exc:
        if str(exc) == "health_exists":
            raise HTTPException(
                status_code=409, detail="Health report already exists for this session"
            )
        raise
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return SessionHealthOut.model_validate(health)


@router.get("/sessions/{session_id}/health", response_model=SessionHealthOut)
async def get_health(
    session_id: int,
    db: AsyncSession = Depends(get_db),
) -> SessionHealthOut:
    """Return the cached context rot health report for a session."""
    health = await get_session_health(session_id, db)
    if health is None:
        raise HTTPException(
            status_code=404,
            detail="No health report found. POST to generate one.",
        )
    return SessionHealthOut.model_validate(health)
