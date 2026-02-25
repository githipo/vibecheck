import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from schemas.session import AnalyticsOut, CatchupOut, CatchupRequest
from services.analytics_service import compute_analytics, generate_catchup_brief

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/analytics", response_model=AnalyticsOut)
async def get_analytics(db: AsyncSession = Depends(get_db)) -> dict:
    """Return aggregated comprehension analytics across all sessions."""
    try:
        result = await compute_analytics(db)
    except Exception as exc:
        logger.error("Failed to compute analytics: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Analytics computation failed: {exc}",
        ) from exc

    return result


@router.post("/analytics/catchup", response_model=CatchupOut)
async def catchup(
    request: CatchupRequest, db: AsyncSession = Depends(get_db)
) -> CatchupOut:
    """Generate a personalized catch-up explanation for a given topic."""
    try:
        brief, source_sessions = await generate_catchup_brief(request.topic, db)
    except Exception as exc:
        logger.error("Failed to generate catch-up brief for topic %r: %s", request.topic, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Catch-up brief generation failed: {exc}",
        ) from exc

    return CatchupOut(
        topic=request.topic,
        brief=brief,
        source_sessions=source_sessions,
    )
