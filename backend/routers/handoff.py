import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.session import Session
from schemas.session import HandoffApplyRequest, SessionHandoffOut
from services.handoff_service import create_handoff, get_handoff

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/sessions/{session_id}/handoff", response_model=SessionHandoffOut, status_code=201)
async def generate_handoff_endpoint(
    session_id: int,
    db: AsyncSession = Depends(get_db),
) -> SessionHandoffOut:
    """Generate a compact handoff document for starting a fresh AI session.

    Returns 409 if a handoff already exists — use GET to retrieve it.
    """
    try:
        handoff = await create_handoff(session_id, db)
    except RuntimeError as exc:
        if str(exc) == "handoff_exists":
            raise HTTPException(
                status_code=409, detail="Handoff already exists for this session"
            )
        raise
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return SessionHandoffOut.model_validate(handoff)


@router.get("/sessions/{session_id}/handoff", response_model=SessionHandoffOut)
async def get_handoff_endpoint(
    session_id: int,
    db: AsyncSession = Depends(get_db),
) -> SessionHandoffOut:
    """Return the cached handoff document for a session."""
    handoff = await get_handoff(session_id, db)
    if handoff is None:
        raise HTTPException(
            status_code=404,
            detail="No handoff generated yet. POST to generate one.",
        )
    return SessionHandoffOut.model_validate(handoff)


@router.post("/sessions/{session_id}/handoff/apply")
async def apply_handoff(
    session_id: int,
    body: HandoffApplyRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Write the handoff document to a file (e.g. HANDOFF.md or CLAUDE.md)."""
    handoff = await get_handoff(session_id, db)
    if handoff is None:
        raise HTTPException(
            status_code=404,
            detail="No handoff generated yet. POST /handoff to generate one first.",
        )

    file_path = body.file_path
    if not os.path.isabs(file_path):
        raise HTTPException(
            status_code=400, detail="file_path must be an absolute path"
        )

    try:
        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write(handoff.content)
            fh.write("\n")
    except OSError as exc:
        raise HTTPException(
            status_code=400, detail=f"Could not write to file: {exc}"
        ) from exc

    logger.info(
        "Handoff for session %d written to %s (%d words)",
        session_id, file_path, handoff.word_count
    )
    return {
        "applied": True,
        "file_path": file_path,
        "word_count": handoff.word_count,
    }
