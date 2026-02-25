import logging
import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.session import FocusArea, Quiz, Session
from schemas.session import (
    CodeQuizRequest,
    FocusAreaCreate,
    FocusAreaOut,
    ScanRequest,
    ScanResult,
    SessionOut,
)
from services.codebase_service import generate_code_quiz, scan_directory

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
