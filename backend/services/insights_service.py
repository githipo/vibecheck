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


_INSIGHTS_SYSTEM_PROMPT = """You are a senior software architect analyzing an AI-assisted coding session transcript.
Your job is to extract structured project intelligence that will help future AI sessions on this codebase start with better context.

Extract the following from the transcript:

1. **decisions** — Architectural or implementation decisions that were made. For each: what was decided, why, and what alternatives were considered and rejected.
2. **patterns** — Coding patterns, conventions, or approaches that were established in this session that should be followed going forward.
3. **gotchas** — Constraints, tricky issues, tradeoffs, or non-obvious things discovered during this session that a future developer or AI should know.
4. **proposed_rules** — 2–5 concrete, actionable rules suitable for a CLAUDE.md file. These should be specific to this project, not generic best practices. Each should have a section label (e.g. "Architecture", "Code Style", "Testing", "Database", "API Design").

Respond with ONLY a JSON object matching this exact schema — no prose, no markdown:
{
  "decisions": [
    { "decision": "...", "rationale": "...", "alternatives_rejected": ["...", "..."] }
  ],
  "patterns": [
    { "pattern": "...", "description": "..." }
  ],
  "gotchas": [
    { "issue": "...", "context": "..." }
  ],
  "proposed_rules": [
    { "rule": "...", "rationale": "...", "section": "..." }
  ]
}"""

_REQUIRED_KEYS = {"decisions", "patterns", "gotchas", "proposed_rules"}


async def extract_insights(transcript: str, session_title: str) -> dict:
    """Call OpenAI to extract structured project intelligence from a session transcript.

    Returns a dict with keys: decisions, patterns, gotchas, proposed_rules.
    Raises ValueError if the AI response is malformed or missing expected keys.
    """
    client = _get_client()

    user_message = f"Session title: {session_title}\n\nTranscript:\n{transcript}"

    logger.info(
        "Requesting session intelligence extraction from OpenAI (model=%s, title=%r)",
        MODEL,
        session_title,
    )

    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": _INSIGHTS_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    raw = response.choices[0].message.content or ""
    logger.debug("OpenAI insights raw response: %s", raw[:500])

    try:
        parsed: dict = json.loads(_extract_json(raw))
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse OpenAI insights response as JSON: %s", exc)
        raise ValueError(f"OpenAI returned invalid JSON for insights: {exc}") from exc

    missing = _REQUIRED_KEYS - set(parsed.keys())
    if missing:
        raise ValueError(
            f"OpenAI insights response missing required keys: {', '.join(sorted(missing))}"
        )

    for key in _REQUIRED_KEYS:
        if not isinstance(parsed[key], list):
            raise ValueError(
                f"OpenAI insights response key '{key}' must be a list, got {type(parsed[key]).__name__}"
            )

    logger.info(
        "Extracted insights: %d decisions, %d patterns, %d gotchas, %d proposed_rules",
        len(parsed["decisions"]),
        len(parsed["patterns"]),
        len(parsed["gotchas"]),
        len(parsed["proposed_rules"]),
    )
    return parsed
