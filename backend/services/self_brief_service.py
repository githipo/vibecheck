import json
import logging
import os

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
    import re

    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return match.group(1).strip()
    return text


_SELF_BRIEF_SYSTEM_PROMPT = """You are generating an AI onboarding brief for a software codebase.

This document is NOT for humans — it is specifically written to help a fresh AI coding assistant (like Claude Code) understand this codebase and avoid common mistakes. Focus on:

1. Things that are non-obvious from reading individual files in isolation
2. Implicit conventions and patterns that ALL code in this project follows
3. Architectural invariants — assumptions the code relies on that would cause subtle bugs if violated
4. Common mistakes an AI would make without this context (e.g. wrong abstraction layer, wrong error handling pattern, missing required fields)
5. The 3-6 most important files/entry points and their exact roles

Then suggest 3-5 specialized sub-agents for this codebase. Each sub-agent should have a focused domain (database, API contracts, frontend state, auth, etc.) and a system prompt that gives it deep context about that domain in THIS specific project — not generic advice.

Respond with ONLY a JSON object — no prose, no markdown fences:
{
  "brief": {
    "architecture_summary": "2-3 sentence description of the overall architecture and how pieces connect",
    "non_obvious_conventions": ["convention 1", "convention 2", ...],
    "critical_invariants": ["invariant 1", ...],
    "common_mistakes_to_avoid": ["mistake 1", ...],
    "key_entry_points": [{"file": "relative/path.py", "role": "description"}, ...]
  },
  "suggested_agents": [
    {
      "name": "short-name-agent",
      "role": "Domain specialist role",
      "description": "One sentence on what this agent knows",
      "system_prompt": "Full system prompt text that would be given to this agent, including specific knowledge about this codebase",
      "claude_md_entry": "Complete CLAUDE.md block ready to paste, including the agent name as a header and its system prompt"
    }
  ]
}"""


async def generate_self_brief(directory: str, file_summaries: list[dict]) -> dict:
    """Generate an AI onboarding brief for a codebase.

    Args:
        directory: Absolute path to the scanned directory.
        file_summaries: List of top-risk file dicts, each with keys:
            path, relative_path, language, risk_score, risk_factors.

    Returns:
        Parsed dict with keys "brief" and "suggested_agents".

    Raises:
        ValueError: If the AI returns invalid JSON or an empty response.
    """
    # Take top 15 by risk_score and read file contents (truncated to 800 chars)
    top_files = sorted(file_summaries, key=lambda f: f.get("risk_score", 0), reverse=True)[:15]

    file_blocks: list[str] = []
    for fdata in top_files:
        rel_path = fdata.get("relative_path", fdata.get("path", ""))
        risk_score = fdata.get("risk_score", 0)
        abs_path = fdata.get("path", "")

        content_truncated = ""
        if abs_path and os.path.isfile(abs_path):
            try:
                with open(abs_path, encoding="utf-8") as fh:
                    content_truncated = fh.read(800)
            except (OSError, UnicodeDecodeError) as exc:
                logger.warning("Could not read %s for self-brief: %s", abs_path, exc)

        file_blocks.append(
            f"--- {rel_path} (risk: {risk_score}) ---\n{content_truncated}"
        )

    user_message = (
        f"Directory: {directory}\n\n"
        "Top files by comprehension risk (with first 800 chars of each):\n\n"
        + "\n\n".join(file_blocks)
    )

    client = _get_client()
    logger.info(
        "Requesting self-brief from OpenAI (model=%s, directory=%s, files=%d)",
        MODEL,
        directory,
        len(top_files),
    )

    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": _SELF_BRIEF_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    raw = response.choices[0].message.content or ""
    logger.debug("OpenAI self-brief raw response: %s", raw[:500])

    try:
        parsed: dict = json.loads(_extract_json(raw))
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse OpenAI self-brief response as JSON: %s", exc)
        raise ValueError(f"OpenAI returned invalid JSON for self-brief: {exc}") from exc

    if not isinstance(parsed, dict) or "brief" not in parsed:
        raise ValueError("OpenAI returned unexpected structure for self-brief")

    logger.info(
        "Self-brief generated for %s with %d suggested agents",
        directory,
        len(parsed.get("suggested_agents", [])),
    )
    return parsed
