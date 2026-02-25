import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import get_db
from models.session import Insight, Session
from schemas.session import ApplyInsightRequest, InsightOut
from services import insights_service

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


async def _get_insight_or_404(session_id: int, db: AsyncSession) -> Insight:
    result = await db.execute(
        select(Insight).where(Insight.session_id == session_id)
    )
    insight = result.scalar_one_or_none()
    if insight is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No insights generated yet for this session",
        )
    return insight


@router.post(
    "/sessions/{session_id}/insights",
    response_model=InsightOut,
    status_code=status.HTTP_201_CREATED,
)
async def generate_insights(
    session_id: int, db: AsyncSession = Depends(get_db)
) -> Insight:
    """Generate Session Intelligence for a session by calling the AI."""
    session = await _get_session_or_404(session_id, db)

    existing_result = await db.execute(
        select(Insight).where(Insight.session_id == session_id)
    )
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Insights already generated for this session",
        )

    try:
        extracted = await insights_service.extract_insights(
            session.transcript, session.title
        )
    except ValueError as exc:
        logger.error("Insight extraction failed for session %d: %s", session_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Insight extraction failed: {exc}",
        ) from exc

    insight = Insight(
        session_id=session_id,
        decisions=extracted["decisions"],
        patterns=extracted["patterns"],
        gotchas=extracted["gotchas"],
        proposed_rules=extracted["proposed_rules"],
    )
    db.add(insight)
    await db.commit()
    await db.refresh(insight)

    logger.info("Insight id=%d generated for session id=%d", insight.id, session_id)
    return insight


@router.get("/sessions/{session_id}/insights", response_model=InsightOut)
async def get_insights(
    session_id: int, db: AsyncSession = Depends(get_db)
) -> Insight:
    """Return the existing insights for a session."""
    await _get_session_or_404(session_id, db)
    return await _get_insight_or_404(session_id, db)


@router.post("/sessions/{session_id}/insights/apply")
async def apply_insights(
    session_id: int,
    body: ApplyInsightRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Append the session's insights as a structured block to a CLAUDE.md file."""
    result = await db.execute(
        select(Session, Insight)
        .join(Insight, Insight.session_id == Session.id)
        .where(Session.id == session_id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No insights generated yet for this session",
        )
    session, insight = row

    file_path = body.file_path

    if not os.path.isabs(file_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="file_path must be an absolute path",
        )
    if not file_path.endswith(".md"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="file_path must point to a .md file",
        )
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File does not exist: {file_path}",
        )

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines: list[str] = [
        "",
        "---",
        "",
        f"## Session Intelligence — {session.title} ({date_str})",
        "",
        "### Architectural Decisions",
    ]

    for d in insight.decisions:
        alternatives = ", ".join(d.get("alternatives_rejected", [])) or "none noted"
        lines.append(f"- **{d['decision']}**: {d['rationale']}")
        lines.append(f"  - Alternatives rejected: {alternatives}")

    lines += ["", "### Patterns Established"]
    for p in insight.patterns:
        lines.append(f"- **{p['pattern']}**: {p['description']}")

    lines += ["", "### Gotchas & Constraints"]
    for g in insight.gotchas:
        lines.append(f"- **{g['issue']}**: {g['context']}")

    lines += ["", "### Rules for Future Sessions", "<!-- Auto-generated by VibeCheck -->"]
    for r in insight.proposed_rules:
        lines.append(f"- {r['rule']}")

    lines.append("")
    block = "\n".join(lines)

    try:
        with open(file_path, "a", encoding="utf-8") as fh:
            fh.write(block)
    except OSError as exc:
        logger.error("Failed to write to %s: %s", file_path, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not write to file: {exc}",
        ) from exc

    chars_added = len(block)
    logger.info(
        "Applied insights for session id=%d to %s (%d chars added)",
        session_id,
        file_path,
        chars_added,
    )
    return {"applied": True, "file_path": file_path, "chars_added": chars_added}
