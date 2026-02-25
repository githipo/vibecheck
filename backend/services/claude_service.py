import json
import logging
import os
import re

import openai
from dotenv import load_dotenv

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


_QUIZ_SYSTEM_PROMPT = """You are an expert learning-verification assistant for VibeCheck.
Your job is to read an AI-assisted coding/design/writing session transcript and generate quiz questions that verify the human actually understands what was built — not just memorized outputs.

Rules for question generation:
- Generate between 3 and 7 questions total.
- Questions MUST require understanding of THIS specific session — they cannot be trivially googled.
- Target key decisions, trade-offs, patterns, and concepts visible in the transcript.
- Vary question types: use a mix of multiple_choice, short_answer, and code_explanation.
- Follow a difficulty curve: start conceptual, end implementation-level.
- Never ask about boilerplate, trivial syntax, or details that don't reflect real understanding.
- For multiple_choice: include exactly 4 choices, and set answer_key to the correct choice text (verbatim from choices).
- For short_answer and code_explanation: omit choices and answer_key.

Respond with ONLY a JSON array — no prose, no markdown fences. Each element must follow this schema exactly:
{
  "id": "<string — q1, q2, ...>",
  "type": "<multiple_choice | short_answer | code_explanation>",
  "question": "<question text>",
  "choices": ["<choice A>", "<choice B>", "<choice C>", "<choice D>"],  // only for multiple_choice
  "answer_key": "<exact text of correct choice>"  // only for multiple_choice
}
"""

_EVAL_SYSTEM_PROMPT = """You are a strict but fair learning-verification evaluator for VibeCheck.
You will receive: the original session transcript, a list of quiz questions, and the user's answers.

For each answer evaluate:
- correctness relative to the transcript (not general knowledge)
- quality of explanation
- partial credit is real — reward partial understanding

Verdict scale:
- "correct": answer demonstrates clear understanding of the concept as it appears in the transcript
- "partial": answer shows some understanding but misses key nuance or is incomplete
- "incorrect": answer is wrong, irrelevant, or shows no understanding

Score scale (0–100):
- correct: 70–100
- partial: 30–69
- incorrect: 0–29

Feedback must be specific and educational — reference the transcript when explaining.

After evaluating all answers, also write a 2–4 sentence feedback_summary about what the user understands well and what they should revisit.

Respond with ONLY a JSON object — no prose, no markdown fences:
{
  "evaluations": [
    {
      "question_id": "<id>",
      "verdict": "<correct|partial|incorrect>",
      "score": <0-100>,
      "feedback": "<specific educational feedback>"
    }
  ],
  "feedback_summary": "<2-4 sentence overall assessment>"
}
"""


async def generate_quiz_questions(
    transcript: str, source_type: str
) -> list[dict]:
    """Call OpenAI to generate 3–7 quiz questions for a session transcript."""
    client = _get_client()

    user_message = (
        f"Source type: {source_type}\n\n"
        f"Transcript:\n{transcript}"
    )

    logger.info("Requesting quiz generation from OpenAI (model=%s)", MODEL)

    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=2048,
        messages=[
            {"role": "system", "content": _QUIZ_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    raw = response.choices[0].message.content or ""
    logger.debug("OpenAI quiz raw response: %s", raw[:500])

    try:
        questions: list[dict] = json.loads(_extract_json(raw))
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse OpenAI quiz response as JSON: %s", exc)
        raise ValueError(f"OpenAI returned invalid JSON for quiz: {exc}") from exc

    if not isinstance(questions, list) or len(questions) == 0:
        raise ValueError("OpenAI returned an empty or non-list quiz response")

    logger.info("Generated %d quiz questions", len(questions))
    return questions


async def evaluate_answers(
    transcript: str,
    questions: list[dict],
    answers: list[dict],
) -> tuple[list[dict], float, str]:
    """Call OpenAI to evaluate user answers against the transcript.

    Returns:
        A tuple of (evaluations, overall_score, feedback_summary).
    """
    client = _get_client()

    user_message = (
        f"Transcript:\n{transcript}\n\n"
        f"Questions:\n{json.dumps(questions, indent=2)}\n\n"
        f"User Answers:\n{json.dumps(answers, indent=2)}"
    )

    logger.info("Requesting answer evaluation from OpenAI (model=%s)", MODEL)

    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": _EVAL_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    raw = response.choices[0].message.content or ""
    logger.debug("OpenAI eval raw response: %s", raw[:500])

    try:
        parsed: dict = json.loads(_extract_json(raw))
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse OpenAI eval response as JSON: %s", exc)
        raise ValueError(f"OpenAI returned invalid JSON for evaluation: {exc}") from exc

    evaluations: list[dict] = parsed.get("evaluations", [])
    feedback_summary: str = parsed.get("feedback_summary", "")

    if not evaluations:
        raise ValueError("OpenAI returned no evaluations")

    scores = [e.get("score", 0) for e in evaluations]
    overall_score = sum(scores) / len(scores) if scores else 0.0

    logger.info(
        "Evaluated %d answers; overall_score=%.1f", len(evaluations), overall_score
    )
    return evaluations, overall_score, feedback_summary
