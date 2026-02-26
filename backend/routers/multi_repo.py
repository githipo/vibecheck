import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import get_db
from models.session import Repo, RepoConnection, RepoGroup
from schemas.session import (
    RepoConnectionOut,
    RepoContextOut,
    RepoGroupCreate,
    RepoGroupDetail,
    RepoGroupOut,
)
from services.multi_repo_service import analyze_group

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /api/repos/groups — list all groups (no repos eager-loaded)
# ---------------------------------------------------------------------------


@router.get("/repos/groups", response_model=list[RepoGroupOut])
async def list_repo_groups(db: AsyncSession = Depends(get_db)) -> list[RepoGroup]:
    """Return all repo groups with their repos, newest first."""
    rows = (
        await db.execute(
            select(RepoGroup)
            .options(selectinload(RepoGroup.repos))
            .order_by(RepoGroup.created_at.desc())
        )
    ).scalars().all()
    return list(rows)


# ---------------------------------------------------------------------------
# POST /api/repos/groups — create group + repos
# ---------------------------------------------------------------------------


@router.post(
    "/repos/groups",
    response_model=RepoGroupOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_repo_group(
    body: RepoGroupCreate, db: AsyncSession = Depends(get_db)
) -> RepoGroup:
    """Create a new repo group with its member repos."""
    group = RepoGroup(name=body.name, description=body.description)
    db.add(group)
    await db.flush()  # get group.id before adding children

    for repo_in in body.repos:
        repo = Repo(
            group_id=group.id,
            name=repo_in.name,
            path=repo_in.path,
            role=repo_in.role,
        )
        db.add(repo)

    await db.commit()
    await db.refresh(group)

    # Reload with repos eager-loaded for the response
    result = await db.execute(
        select(RepoGroup)
        .where(RepoGroup.id == group.id)
        .options(selectinload(RepoGroup.repos))
    )
    group = result.scalar_one()
    logger.info(
        "Created RepoGroup id=%d name=%r with %d repos",
        group.id,
        group.name,
        len(group.repos),
    )
    return group


# ---------------------------------------------------------------------------
# GET /api/repos/groups/{id} — group detail with repos
# ---------------------------------------------------------------------------


@router.get("/repos/groups/{group_id}", response_model=RepoGroupDetail)
async def get_repo_group(
    group_id: int, db: AsyncSession = Depends(get_db)
) -> dict:
    """Return a single repo group with repos and existing connections."""
    result = await db.execute(
        select(RepoGroup)
        .where(RepoGroup.id == group_id)
        .options(
            selectinload(RepoGroup.repos),
            selectinload(RepoGroup.connections),
        )
    )
    group: RepoGroup | None = result.scalar_one_or_none()

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RepoGroup {group_id} not found",
        )

    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "created_at": group.created_at,
        "repos": group.repos,
        "connections": group.connections,
    }


# ---------------------------------------------------------------------------
# DELETE /api/repos/groups/{id} — delete group + repos + connections
# ---------------------------------------------------------------------------


@router.delete("/repos/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repo_group(
    group_id: int, db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a repo group and all its repos and connections (cascade)."""
    group = await db.get(RepoGroup, group_id)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RepoGroup {group_id} not found",
        )
    await db.delete(group)
    await db.commit()
    logger.info("Deleted RepoGroup id=%d", group_id)


# ---------------------------------------------------------------------------
# POST /api/repos/groups/{id}/analyze — trigger AI analysis, save connections
# ---------------------------------------------------------------------------


@router.post(
    "/repos/groups/{group_id}/analyze",
    response_model=RepoGroupDetail,
)
async def analyze_repo_group(
    group_id: int, db: AsyncSession = Depends(get_db)
) -> dict:
    """Run AI analysis to detect cross-repo connections. Saves results to DB."""
    # Verify group exists first for a clean 404 before the service call
    exists = await db.get(RepoGroup, group_id)
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RepoGroup {group_id} not found",
        )

    try:
        analysis = await analyze_group(group_id=group_id, db=db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Multi-repo analysis failed for group %d: %s", group_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Multi-repo analysis failed: {exc}",
        ) from exc

    # Reload group with fresh connections after analysis
    result = await db.execute(
        select(RepoGroup)
        .where(RepoGroup.id == group_id)
        .options(
            selectinload(RepoGroup.repos),
            selectinload(RepoGroup.connections),
        )
    )
    group: RepoGroup = result.scalar_one()

    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "created_at": group.created_at,
        "repos": group.repos,
        "connections": group.connections,
    }


# ---------------------------------------------------------------------------
# GET /api/repos/groups/{id}/context — return context for current session
# ---------------------------------------------------------------------------


@router.get("/repos/groups/{group_id}/context", response_model=RepoContextOut)
async def get_repo_context(
    group_id: int, db: AsyncSession = Depends(get_db)
) -> dict:
    """Return the stored cross-repo context (last analysis result) for a group."""
    result = await db.execute(
        select(RepoGroup)
        .where(RepoGroup.id == group_id)
        .options(
            selectinload(RepoGroup.repos),
            selectinload(RepoGroup.connections),
        )
    )
    group: RepoGroup | None = result.scalar_one_or_none()

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RepoGroup {group_id} not found",
        )

    connections: list[RepoConnection] = list(group.connections)

    # Build repo_briefs from repo roles (static — AI briefs are in analysis result)
    repo_briefs: dict[str, str] = {
        repo.name: repo.role for repo in group.repos
    }

    # Derive a summary from the connections if any exist
    if connections:
        summary = (
            f"Group '{group.name}' has {len(connections)} detected cross-repo "
            f"connection(s) across {len(group.repos)} repo(s). "
            f"Run POST /analyze to refresh."
        )
    else:
        summary = (
            f"No connections detected yet for group '{group.name}'. "
            f"Run POST /analyze to discover cross-repo relationships."
        )

    return {
        "group_name": group.name,
        "summary": summary,
        "connections": connections,
        "repo_briefs": repo_briefs,
    }
