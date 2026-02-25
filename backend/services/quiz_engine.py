import logging

from sqlalchemy.ext.asyncio import AsyncSession

from models.session import Attempt, Quiz, Session
from services.claude_service import evaluate_answers, generate_quiz_questions

logger = logging.getLogger(__name__)


async def create_quiz_for_session(session: Session, db: AsyncSession) -> Quiz:
    """Generate a quiz for the given session via Claude and persist it to the DB.

    Updates session status to 'quiz_active' after the quiz is created.

    Args:
        session: The ORM Session object whose transcript will be quizzed.
        db: The active async database session.

    Returns:
        The newly created Quiz ORM object.
    """
    logger.info("Generating quiz for session id=%d", session.id)

    questions = await generate_quiz_questions(session.transcript, session.source_type)

    quiz = Quiz(session_id=session.id, questions=questions)
    db.add(quiz)

    session.status = "quiz_active"
    db.add(session)

    await db.commit()
    await db.refresh(quiz)

    logger.info("Quiz id=%d created for session id=%d", quiz.id, session.id)
    return quiz


async def submit_attempt(
    session: Session,
    quiz: Quiz,
    answers: list[dict],
    db: AsyncSession,
) -> Attempt:
    """Evaluate user answers via Claude and persist the Attempt to the DB.

    Updates session status to 'completed' after the attempt is recorded.

    Args:
        session: The ORM Session object.
        quiz: The ORM Quiz object whose questions are being answered.
        answers: List of answer dicts with keys question_id and answer_text.
        db: The active async database session.

    Returns:
        The newly created Attempt ORM object.
    """
    logger.info(
        "Submitting attempt for session id=%d, quiz id=%d", session.id, quiz.id
    )

    evaluations, overall_score, feedback_summary = await evaluate_answers(
        transcript=session.transcript,
        questions=quiz.questions,
        answers=answers,
    )

    attempt = Attempt(
        session_id=session.id,
        quiz_id=quiz.id,
        answers=answers,
        evaluations=evaluations,
        score=overall_score,
        feedback_summary=feedback_summary,
    )
    db.add(attempt)

    session.status = "completed"
    db.add(session)

    await db.commit()
    await db.refresh(attempt)

    logger.info(
        "Attempt id=%d saved; score=%.1f for session id=%d",
        attempt.id,
        overall_score,
        session.id,
    )
    return attempt
