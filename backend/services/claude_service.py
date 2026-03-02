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


_HANDOFF_SYSTEM_PROMPT = """You are a context compression expert for AI coding sessions. Your job: given a long, expensive conversation transcript, distill it into a compact handoff document that lets a developer start a FRESH AI session without losing any important context.

The handoff document must:
- Be under 500 words total (tight — every word earns its place)
- Be written as a ready-to-paste opening message for a new AI coding session
- Focus on STATE and NEXT STEPS, not conversation history
- Allow someone who has NEVER seen the original conversation to pick up exactly where it left off

Format the document in Markdown using exactly these sections:

# Handoff: [infer a specific title from the work done]

## What we built
[2–5 bullet points of concrete accomplishments — files created or modified, features added, bugs fixed]

## Decisions (don't revisit these)
[2–5 bullet points: what was decided and the key reason why — especially architectural or irreversible choices]

## Current state
[1–3 sentences: exactly where things stand right now. What works. What's broken. What's in progress.]

## Next steps
[2–5 numbered tasks, most critical first. Be specific — name files, functions, or endpoints.]

## Constraints
[Bullet list of gotchas, patterns to follow, or things NOT to do based on what was learned this session. Omit if none.]

## Key files
[Only files that matter going forward: `path/to/file` — one sentence on its role or what changed]

Be specific and concrete. Avoid generic advice. Name actual files, functions, and decisions from the transcript."""


async def generate_handoff(transcript: str, title: str) -> str:
    """Call OpenAI to compress a session transcript into a compact handoff document.

    Returns the handoff as a markdown string.
    """
    client = _get_client()

    user_message = f"Session title: {title}\n\nTranscript:\n{transcript}"

    logger.info("Requesting handoff generation from OpenAI (model=%s)", MODEL)

    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=1500,
        messages=[
            {"role": "system", "content": _HANDOFF_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    content = response.choices[0].message.content or ""
    logger.debug("OpenAI handoff raw response: %s", content[:300])
    logger.info("Generated handoff (%d chars)", len(content))
    return content.strip()


_CONTEXT_ROT_SYSTEM_PROMPT = """You are a session health analyzer for VibeCheck. Your job is to analyze AI coding session transcripts and identify "context rot" — habits that waste tokens and degrade AI response quality over long conversations.

Background: every AI response re-reads the entire conversation history first. A 100-message conversation means message 100 is paying to re-read messages 1-99 before adding anything new. Vague, one-word prompts are the worst offenders — they force the AI to guess your intent from an ever-growing history.

Key patterns to identify:

LAZY PROMPTS — short, vague user messages with no actionable specifics:
- Single-word confirmations: "Yes", "No", "Ok", "Sure", "Go", "Continue", "Proceed"
- Empty affirmations: "Sounds good", "Looks good", "Perfect", "Great", "Nice", "Cool"
- Vague directives: "Do it", "Just do it", "Go ahead", "Keep going"
- Filler responses: "Thanks", "Thank you", "Got it", "I see"
- Messages under ~15 characters that provide no new information or direction

CONTEXT BREAKPOINTS — natural topic shifts where starting a fresh session would save tokens and improve focus.

Parse the transcript carefully. Look for lines starting with "Human:", "User:", or other user prefixes. If there are no clear prefixes, use your best judgment about which messages are from the human vs the AI.

Compute:
- total_messages: total turns in the conversation (user + AI combined)
- user_messages: only the user's turns
- lazy_prompt_count: how many user messages match the lazy patterns
- efficiency_score: 0–100. 100 = every user message is specific and adds clear direction. Deduct points for lazy prompts (weighted by position — later lazy prompts cost more), for marathon length (over 50 total messages), and for missed breakpoints.
- estimated_wasted_token_ratio: rough fraction of tokens wasted on re-reading context for lazy prompts. Approximation: for a lazy prompt at position P out of N total, that message wasted P/N of the session's re-read budget. Sum across all lazy prompts, cap at 0.95.

Respond with ONLY a JSON object — no prose, no markdown fences:
{
  "total_messages": <int>,
  "user_messages": <int>,
  "lazy_prompt_count": <int>,
  "efficiency_score": <0-100 float>,
  "estimated_wasted_token_ratio": <0.0-1.0 float>,
  "lazy_prompts": [
    {
      "text": "<exact quote from transcript>",
      "position": <1-indexed message number>,
      "reason": "<one sentence explaining why this wastes tokens>",
      "suggested_rewrite": "<specific, actionable alternative that provides clear direction>"
    }
  ],
  "breakpoints": [
    {
      "message_num": <int>,
      "reason": "<why this was a natural stopping point>",
      "context": "<what topic/task was wrapping up here>"
    }
  ],
  "summary": "<2-4 sentence narrative assessing the session's context health. Be specific about the worst habits and the potential savings.>"
}
"""


async def analyze_context_rot(transcript: str) -> dict:
    """Call OpenAI to analyze a session transcript for context rot patterns.

    Returns a dict with efficiency_score, lazy_prompts, breakpoints, and summary.
    """
    client = _get_client()

    logger.info("Requesting context rot analysis from OpenAI (model=%s)", MODEL)

    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": _CONTEXT_ROT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Transcript:\n{transcript}"},
        ],
    )

    raw = response.choices[0].message.content or ""
    logger.debug("OpenAI context rot raw response: %s", raw[:500])

    try:
        result: dict = json.loads(_extract_json(raw))
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse OpenAI context rot response as JSON: %s", exc)
        raise ValueError(f"OpenAI returned invalid JSON for context rot analysis: {exc}") from exc

    return result


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
