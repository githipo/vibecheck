import json
import logging
import os
import re

import openai
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.session import Attempt, Quiz, Session

load_dotenv()

logger = logging.getLogger(__name__)

MODEL = "gpt-4o"

_client: openai.AsyncOpenAI | None = None


def _get_client() -> openai.AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set")
        _client = openai.AsyncOpenAI(api_key=api_key)
    return _client


def _extract_json(text: str) -> str:
    """Strip markdown code fences if the model wrapped the JSON in them."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return match.group(1).strip()
    return text


_TOPIC_CLASSIFIER_SYSTEM_PROMPT = (
    "You are classifying quiz questions into broad technical topics. "
    "For each question, output one short topic label (2-4 words max). "
    "Use consistent labels across questions — prefer: 'Security', 'Async Patterns', "
    "'Database Design', 'API Design', 'Error Handling', 'Authentication', "
    "'Data Modeling', 'Testing', 'Architecture', 'Performance'. "
    "If nothing fits, use 'General Concepts'. "
    "Respond with ONLY a JSON array of strings, one label per question, in the same order."
)


async def _classify_questions(question_texts: list[str]) -> list[str]:
    """Call OpenAI to classify a list of question texts into topic labels.

    Returns a list of topic strings in the same order as the input.
    Falls back to 'General Concepts' for any classification failure.
    """
    if not question_texts:
        return []

    client = _get_client()

    numbered = "\n".join(
        f"{i + 1}. {q}" for i, q in enumerate(question_texts)
    )

    logger.info(
        "Requesting topic classification from OpenAI (model=%s, count=%d)",
        MODEL,
        len(question_texts),
    )

    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": _TOPIC_CLASSIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": numbered},
        ],
    )

    raw = response.choices[0].message.content or ""
    logger.debug("OpenAI topic classification raw response: %s", raw[:500])

    try:
        topics: list[str] = json.loads(_extract_json(raw))
        if not isinstance(topics, list):
            raise ValueError("Expected a JSON array")
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("Failed to parse topic classification response: %s", exc)
        return ["General Concepts"] * len(question_texts)

    # Pad or trim to match input length
    if len(topics) < len(question_texts):
        topics += ["General Concepts"] * (len(question_texts) - len(topics))
    return topics[: len(question_texts)]


async def compute_analytics(db: AsyncSession) -> dict:
    """Aggregate comprehension analytics across all sessions and attempts.

    Returns a dict matching the AnalyticsOut schema.
    """
    # -----------------------------------------------------------------------
    # 1. Load all sessions
    # -----------------------------------------------------------------------
    session_rows = (await db.execute(select(Session))).scalars().all()
    total_sessions = len(session_rows)
    session_map: dict[int, Session] = {s.id: s for s in session_rows}

    # -----------------------------------------------------------------------
    # 2. Load all quizzes — build question lookup: question_id -> question dict
    # -----------------------------------------------------------------------
    quiz_rows = (await db.execute(select(Quiz))).scalars().all()
    # Map (quiz_id, question_id) -> question dict
    question_lookup: dict[tuple[int, str | int], dict] = {}
    quiz_session_map: dict[int, int] = {}  # quiz_id -> session_id
    for quiz in quiz_rows:
        quiz_session_map[quiz.id] = quiz.session_id
        for q in (quiz.questions or []):
            question_lookup[(quiz.id, q.get("id"))] = q

    # -----------------------------------------------------------------------
    # 3. Load all attempts — flatten evaluations
    # -----------------------------------------------------------------------
    attempt_rows = (await db.execute(select(Attempt))).scalars().all()

    if not attempt_rows:
        logger.info("No attempts found — returning zeroed analytics")
        return {
            "total_sessions": total_sessions,
            "completed_sessions": 0,
            "total_questions_answered": 0,
            "overall_avg_score": 0.0,
            "topic_scores": [],
            "blind_spots": [],
            "trend": [],
        }

    # Build flat list of enriched evaluation entries
    flat_evals: list[dict] = []
    sessions_with_attempts: set[int] = set()

    for attempt in attempt_rows:
        sessions_with_attempts.add(attempt.session_id)
        session = session_map.get(attempt.session_id)
        session_title = session.title if session else f"Session {attempt.session_id}"
        created_date = (
            attempt.created_at.date().isoformat() if attempt.created_at else ""
        )

        for ev in (attempt.evaluations or []):
            qid = ev.get("question_id")
            q_dict = question_lookup.get((attempt.quiz_id, qid), {})
            flat_evals.append(
                {
                    "question_id": qid,
                    "quiz_id": attempt.quiz_id,
                    "question_text": q_dict.get("question", ""),
                    "session_id": attempt.session_id,
                    "session_title": session_title,
                    "score": ev.get("score", 0),
                    "verdict": ev.get("verdict", "incorrect"),
                    "date": created_date,
                }
            )

    # -----------------------------------------------------------------------
    # 4. Classify unique questions by topic (single batch call)
    # -----------------------------------------------------------------------
    unique_texts: list[str] = []
    seen: dict[str, int] = {}  # text -> index in unique_texts
    for ev in flat_evals:
        text = ev["question_text"]
        if text not in seen:
            seen[text] = len(unique_texts)
            unique_texts.append(text)

    topic_labels = await _classify_questions(unique_texts)
    text_to_topic: dict[str, str] = {
        text: topic_labels[i] for text, i in seen.items()
    }

    for ev in flat_evals:
        ev["topic"] = text_to_topic.get(ev["question_text"], "General Concepts")

    # -----------------------------------------------------------------------
    # 5. Compute per-topic stats
    # -----------------------------------------------------------------------
    topic_data: dict[str, dict] = {}  # topic -> aggregation dict
    for ev in flat_evals:
        topic = ev["topic"]
        if topic not in topic_data:
            topic_data[topic] = {
                "scores": [],
                "session_ids": set(),
            }
        topic_data[topic]["scores"].append(ev["score"])
        topic_data[topic]["session_ids"].add(ev["session_id"])

    topic_scores: list[dict] = []
    for topic, data in topic_data.items():
        scores = data["scores"]
        avg = sum(scores) / len(scores) if scores else 0.0
        count = len(scores)
        sessions_in = len(data["session_ids"])
        is_blind_spot = avg < 60 and count >= 2
        topic_scores.append(
            {
                "topic": topic,
                "avg_score": round(avg, 2),
                "question_count": count,
                "sessions_appeared_in": sessions_in,
                "is_blind_spot": is_blind_spot,
            }
        )

    blind_spots = [t for t in topic_scores if t["is_blind_spot"]]

    # -----------------------------------------------------------------------
    # 6. Compute trend — latest attempt per session, sorted by date
    # -----------------------------------------------------------------------
    latest_attempt_per_session: dict[int, Attempt] = {}
    for attempt in attempt_rows:
        sid = attempt.session_id
        existing = latest_attempt_per_session.get(sid)
        if existing is None or attempt.created_at > existing.created_at:
            latest_attempt_per_session[sid] = attempt

    trend: list[dict] = []
    for sid, attempt in latest_attempt_per_session.items():
        session = session_map.get(sid)
        trend.append(
            {
                "session_id": sid,
                "title": session.title if session else f"Session {sid}",
                "score": round(attempt.score, 2),
                "date": (
                    attempt.created_at.date().isoformat()
                    if attempt.created_at
                    else ""
                ),
            }
        )
    trend.sort(key=lambda x: x["date"])

    # -----------------------------------------------------------------------
    # 7. Overall stats
    # -----------------------------------------------------------------------
    all_scores = [ev["score"] for ev in flat_evals]
    overall_avg = sum(all_scores) / len(all_scores) if all_scores else 0.0

    logger.info(
        "Analytics computed: %d sessions, %d completed, %d questions, %.1f avg",
        total_sessions,
        len(sessions_with_attempts),
        len(flat_evals),
        overall_avg,
    )

    return {
        "total_sessions": total_sessions,
        "completed_sessions": len(sessions_with_attempts),
        "total_questions_answered": len(flat_evals),
        "overall_avg_score": round(overall_avg, 2),
        "topic_scores": topic_scores,
        "blind_spots": blind_spots,
        "trend": trend,
    }


_CATCHUP_SYSTEM_PROMPT = (
    "You are a personalized tutor for a software developer who is learning through "
    "AI-assisted coding (vibecoding). Based on the specific quiz questions they got "
    "wrong and the actual code sessions they were working on, write a focused 3-4 "
    "paragraph catch-up explanation. Be concrete and reference their actual code. "
    "Do NOT be generic. Explain WHY the concept matters in the context of what they "
    "built. End with one actionable thing they should do or read next."
)


async def generate_catchup_brief(
    topic: str, db: AsyncSession
) -> tuple[str, list[int]]:
    """Generate a personalized catch-up explanation for a given topic.

    Re-classifies all questions to find those matching the topic, then builds
    context from wrong/partial answers and session transcripts.

    Returns (brief_text, list_of_session_ids).
    """
    # -----------------------------------------------------------------------
    # 1. Load quizzes and attempts
    # -----------------------------------------------------------------------
    quiz_rows = (await db.execute(select(Quiz))).scalars().all()
    attempt_rows = (await db.execute(select(Attempt))).scalars().all()

    if not attempt_rows:
        return (
            f"No quiz attempts found yet. Complete some quizzes first, then come back for a {topic} catch-up.",
            [],
        )

    # Build question lookup
    question_lookup: dict[tuple[int, str | int], dict] = {}
    for quiz in quiz_rows:
        for q in (quiz.questions or []):
            question_lookup[(quiz.id, q.get("id"))] = q

    # Build answer lookup: (quiz_id, question_id) -> answer_text from attempts
    answer_lookup: dict[tuple[int, str | int], str] = {}
    for attempt in attempt_rows:
        for ans in (attempt.answers or []):
            key = (attempt.quiz_id, ans.get("question_id"))
            answer_lookup[key] = ans.get("answer_text", "")

    # Flatten evaluations with question text
    flat_evals: list[dict] = []
    for attempt in attempt_rows:
        for ev in (attempt.evaluations or []):
            qid = ev.get("question_id")
            q_dict = question_lookup.get((attempt.quiz_id, qid), {})
            q_text = q_dict.get("question", "")
            answer_text = answer_lookup.get((attempt.quiz_id, qid), "")
            flat_evals.append(
                {
                    "question_id": qid,
                    "quiz_id": attempt.quiz_id,
                    "question_text": q_text,
                    "answer_text": answer_text,
                    "session_id": attempt.session_id,
                    "score": ev.get("score", 0),
                    "verdict": ev.get("verdict", "incorrect"),
                    "feedback": ev.get("feedback", ""),
                }
            )

    # -----------------------------------------------------------------------
    # 2. Classify all unique questions to find topic matches
    # -----------------------------------------------------------------------
    unique_texts: list[str] = []
    seen: dict[str, int] = {}
    for ev in flat_evals:
        text = ev["question_text"]
        if text not in seen:
            seen[text] = len(unique_texts)
            unique_texts.append(text)

    topic_labels = await _classify_questions(unique_texts)
    text_to_topic: dict[str, str] = {
        text: topic_labels[i] for text, i in seen.items()
    }

    # Filter to evals matching the requested topic and verdict partial/incorrect
    wrong_evals = [
        ev
        for ev in flat_evals
        if (
            text_to_topic.get(ev["question_text"], "General Concepts").lower()
            == topic.lower()
            and ev["verdict"] in ("partial", "incorrect")
        )
    ]

    if not wrong_evals:
        return (
            f"Great news — no wrong or partial answers found for the topic '{topic}'. "
            "Either you aced it or haven't been quizzed on it yet.",
            [],
        )

    # -----------------------------------------------------------------------
    # 3. Gather session transcripts for context
    # -----------------------------------------------------------------------
    source_session_ids = list({ev["session_id"] for ev in wrong_evals})
    session_rows = (
        await db.execute(
            select(Session).where(Session.id.in_(source_session_ids))
        )
    ).scalars().all()
    session_map: dict[int, Session] = {s.id: s for s in session_rows}

    # -----------------------------------------------------------------------
    # 4. Build structured context for the AI
    # -----------------------------------------------------------------------
    context_parts: list[str] = [
        f"Topic: {topic}",
        "",
        "WRONG / PARTIAL ANSWERS:",
    ]
    for ev in wrong_evals:
        context_parts.append(f"  Question: {ev['question_text']}")
        context_parts.append(f"  User's answer: {ev['answer_text']}")
        context_parts.append(f"  Verdict: {ev['verdict']} (score {ev['score']}/100)")
        context_parts.append(f"  Feedback: {ev['feedback']}")
        context_parts.append("")

    context_parts.append("RELEVANT SESSION TRANSCRIPTS (truncated to 2000 chars each):")
    for sid in source_session_ids:
        session = session_map.get(sid)
        if session:
            snippet = session.transcript[:2000]
            context_parts.append(f"\n--- Session {sid}: {session.title} ---")
            context_parts.append(snippet)

    user_message = "\n".join(context_parts)

    # -----------------------------------------------------------------------
    # 5. Call OpenAI for the catch-up brief
    # -----------------------------------------------------------------------
    client = _get_client()

    logger.info(
        "Requesting catch-up brief from OpenAI (model=%s, topic=%r)", MODEL, topic
    )

    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=2048,
        messages=[
            {"role": "system", "content": _CATCHUP_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    brief = (response.choices[0].message.content or "").strip()
    logger.info(
        "Catch-up brief generated for topic=%r, source_sessions=%s",
        topic,
        source_session_ids,
    )

    return brief, source_session_ids
