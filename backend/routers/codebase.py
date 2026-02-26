import logging
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.session import FocusArea, Quiz, Session
from schemas.session import (
    ApplySelfBriefRequest,
    CodeQuizRequest,
    FocusAreaCreate,
    FocusAreaOut,
    ScanRequest,
    ScanResult,
    SelfBriefOut,
    SessionOut,
)
from services.codebase_service import generate_code_quiz, scan_directory
from services.self_brief_service import generate_self_brief

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/codebase/scan", response_model=ScanResult)
async def scan_codebase(
    request: ScanRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    """Scan a directory and rank files by comprehension risk."""
    if not os.path.isdir(request.directory):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Directory does not exist or is not accessible: {request.directory}",
        )

    focus_rows = (
        await db.execute(
            select(FocusArea).where(FocusArea.type == "file")
        )
    ).scalars().all()
    focus_paths = [fa.value for fa in focus_rows]

    try:
        result = await scan_directory(
            directory=request.directory,
            extensions=request.extensions,
            max_files=request.max_files,
            focus_paths=focus_paths,
        )
    except Exception as exc:
        logger.error("Codebase scan failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Codebase scan failed: {exc}",
        ) from exc

    return result


@router.get("/focus", response_model=list[FocusAreaOut])
async def list_focus_areas(db: AsyncSession = Depends(get_db)) -> list[FocusArea]:
    """Return all focus areas, newest first."""
    rows = (
        await db.execute(select(FocusArea).order_by(FocusArea.created_at.desc()))
    ).scalars().all()
    return list(rows)


@router.post("/focus", response_model=FocusAreaOut, status_code=status.HTTP_201_CREATED)
async def create_focus_area(
    body: FocusAreaCreate, db: AsyncSession = Depends(get_db)
) -> FocusArea:
    """Pin a file or concept as a focus area."""
    focus = FocusArea(type=body.type, value=body.value, label=body.label)
    db.add(focus)
    await db.commit()
    await db.refresh(focus)
    logger.info("Created FocusArea id=%d type=%s value=%s", focus.id, focus.type, focus.value)
    return focus


@router.delete("/focus/{focus_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_focus_area(
    focus_id: int, db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a focus area by id."""
    focus = await db.get(FocusArea, focus_id)
    if focus is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FocusArea {focus_id} not found",
        )
    await db.delete(focus)
    await db.commit()
    logger.info("Deleted FocusArea id=%d", focus_id)


@router.post(
    "/codebase/quiz", response_model=SessionOut, status_code=status.HTTP_201_CREATED
)
async def create_code_quiz(
    body: CodeQuizRequest, db: AsyncSession = Depends(get_db)
) -> Session:
    """Generate a comprehension quiz directly from a source code file."""
    file_path = body.file_path

    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File does not exist or is not readable: {file_path}",
        )

    try:
        with open(file_path, encoding="utf-8") as fh:
            file_contents = fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot read file: {exc}",
        ) from exc

    title = body.title or os.path.basename(file_path)

    # Create session
    session = Session(
        title=title,
        transcript=file_contents,
        source_type="code_file",
        status="pending_quiz",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    logger.info("Created Session id=%d (source_type=code_file) for %s", session.id, file_path)

    # Generate quiz questions
    try:
        questions = await generate_code_quiz(file_path, title)
    except Exception as exc:
        logger.error("Code quiz generation failed for %s: %s", file_path, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Code quiz generation failed: {exc}",
        ) from exc

    # Save quiz
    quiz = Quiz(session_id=session.id, questions=questions)
    db.add(quiz)

    # Update session status
    session.status = "quiz_active"
    db.add(session)

    await db.commit()
    await db.refresh(session)
    logger.info(
        "Quiz created (id=%d) with %d questions for session id=%d",
        quiz.id,
        len(questions),
        session.id,
    )

    return session


@router.post("/codebase/brief", response_model=SelfBriefOut)
async def generate_brief(
    request: ScanRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    """Generate an AI onboarding brief for a codebase directory."""
    if not os.path.isdir(request.directory):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Directory does not exist or is not accessible: {request.directory}",
        )

    focus_rows = (
        await db.execute(select(FocusArea).where(FocusArea.type == "file"))
    ).scalars().all()
    focus_paths = [fa.value for fa in focus_rows]

    try:
        scan_result = await scan_directory(
            directory=request.directory,
            extensions=request.extensions,
            max_files=request.max_files,
            focus_paths=focus_paths,
        )
    except Exception as exc:
        logger.error("Codebase scan failed during brief generation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Codebase scan failed: {exc}",
        ) from exc

    top_files = scan_result["files"][:15]

    try:
        brief_data = await generate_self_brief(
            directory=request.directory,
            file_summaries=top_files,
        )
    except Exception as exc:
        logger.error("Self-brief generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Self-brief generation failed: {exc}",
        ) from exc

    return {
        "directory": request.directory,
        "brief": brief_data["brief"],
        "suggested_agents": brief_data.get("suggested_agents", []),
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.post("/codebase/brief/apply")
async def apply_brief(body: ApplySelfBriefRequest) -> dict:
    """Append an AI onboarding brief (and optionally sub-agents) to a CLAUDE.md file."""
    file_path = body.file_path

    if not os.path.isabs(file_path):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="file_path must be an absolute path",
        )
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File does not exist: {file_path}",
        )
    if not file_path.endswith(".md"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="file_path must end in .md",
        )

    date_str = datetime.utcnow().strftime("%Y-%m-%d")

    lines: list[str] = [
        "",
        "---",
        "",
        f"## AI Onboarding Brief — {date_str}",
        "",
        "> Auto-generated by VibeCheck. Helps AI assistants understand this codebase.",
        "",
        "### Architecture",
        body.brief.architecture_summary,
        "",
        "### Non-Obvious Conventions",
    ]
    for convention in body.brief.non_obvious_conventions:
        lines.append(f"- {convention}")

    lines.append("")
    lines.append("### Critical Invariants")
    for invariant in body.brief.critical_invariants:
        lines.append(f"- {invariant}")

    lines.append("")
    lines.append("### Common AI Mistakes to Avoid")
    for mistake in body.brief.common_mistakes_to_avoid:
        lines.append(f"- {mistake}")

    lines.append("")
    lines.append("### Key Entry Points")
    for entry in body.brief.key_entry_points:
        lines.append(f"- **{entry.file}**: {entry.role}")

    if body.include_agents and body.suggested_agents:
        lines.append("")
        lines.append("### Suggested Sub-Agents")
        lines.append("")
        for agent in body.suggested_agents:
            lines.append(agent.claude_md_entry)
            lines.append("")

    block = "\n".join(lines) + "\n"

    try:
        with open(file_path, "a", encoding="utf-8") as fh:
            fh.write(block)
    except OSError as exc:
        logger.error("Failed to write brief to %s: %s", file_path, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write to file: {exc}",
        ) from exc

    chars_added = len(block)
    logger.info(
        "Applied self-brief to %s (%d chars added, agents=%s)",
        file_path,
        chars_added,
        body.include_agents,
    )
    return {"applied": True, "file_path": file_path, "chars_added": chars_added}
