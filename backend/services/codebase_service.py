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


_SKIP_DIRS = {"node_modules", ".venv", "__pycache__", ".git", "dist", "build", ".next"}

_EXT_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
}

_IMPORT_PREFIXES = ("import ", "from ", "require(", "use ")

_RISK_SYSTEM_PROMPT = """You are a code comprehension risk assessor. For each numbered file below, assess how likely a developer is to misunderstand it and what the impact would be if they did.

Return ONLY a JSON array with one object per file in the same order:
[
  {
    "index": 0,
    "risk_score": 0-100,
    "risk_factors": ["factor1", "factor2"],
    "blast_radius": "one sentence about impact if misunderstood"
  }
]

Risk score guide:
- 80-100: Complex logic, non-obvious patterns, critical path, no comments
- 60-79: Moderate complexity, some non-obvious parts, or high coupling
- 40-59: Understandable with effort, moderate coupling
- 0-39: Clear, well-structured, low coupling"""

_CODE_QUIZ_SYSTEM_PROMPT = """You are generating comprehension quiz questions directly from a source code file.
The developer may have written this code with AI assistance and needs to verify they understand it.

Rules:
- Generate 3–5 questions targeting the most important and non-obvious parts of this code
- Question types: multiple_choice, short_answer, code_explanation
- Questions should test real understanding: "What would break if X?", "Why is Y done this way?", "What does this function return when Z?"
- Never ask about trivial syntax or boilerplate
- For multiple_choice: exactly 4 choices, set answer_key to the correct choice verbatim

Respond with ONLY a JSON array — same schema as always:
[{"id": "q1", "type": "...", "question": "...", "choices": [...], "answer_key": "..."}]"""


def _infer_language(ext: str) -> str:
    return _EXT_TO_LANGUAGE.get(ext.lower(), ext.lstrip(".") or "unknown")


def _count_imports(lines: list[str]) -> int:
    count = 0
    for line in lines:
        stripped = line.lstrip()
        if any(stripped.startswith(prefix) for prefix in _IMPORT_PREFIXES):
            count += 1
    return count


def _metric_based_score(import_count: int, line_count: int, import_weight: int) -> float:
    """Fallback risk score when AI assessment is unavailable."""
    return min(100.0, import_weight * 10 + min(line_count / 5, 50))


async def scan_directory(
    directory: str,
    extensions: list[str],
    max_files: int,
    focus_paths: list[str],
) -> dict:
    """Scan a directory for files and assess comprehension risk.

    Returns a dict matching the ScanResult schema.
    """
    # ------------------------------------------------------------------
    # Step 1 — Discover files
    # ------------------------------------------------------------------
    discovered: list[tuple[str, int]] = []  # (abs_path, size_bytes)
    ext_set = {e.lower() for e in extensions}

    for dirpath, dirnames, filenames in os.walk(directory):
        # Prune skip dirs in-place to prevent descending into them
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for filename in filenames:
            _, ext = os.path.splitext(filename)
            if ext.lower() in ext_set:
                abs_path = os.path.join(dirpath, filename)
                try:
                    size = os.path.getsize(abs_path)
                except OSError:
                    size = 0
                discovered.append((abs_path, size))

    # Cap at max_files — take largest files first
    if len(discovered) > max_files:
        discovered.sort(key=lambda x: x[1], reverse=True)
        discovered = discovered[:max_files]

    file_paths = [p for p, _ in discovered]

    if not file_paths:
        return {
            "root": directory,
            "file_count": 0,
            "files": [],
        }

    logger.info("Discovered %d files to scan in %s", len(file_paths), directory)

    # ------------------------------------------------------------------
    # Step 2 — Compute code metrics per file
    # ------------------------------------------------------------------
    file_data: list[dict] = []
    stems: dict[str, list[int]] = {}  # stem -> indices of files with that stem

    for idx, abs_path in enumerate(file_paths):
        _, ext = os.path.splitext(abs_path)
        language = _infer_language(ext)
        rel_path = os.path.relpath(abs_path, directory)
        stem = os.path.splitext(os.path.basename(abs_path))[0]

        try:
            with open(abs_path, encoding="utf-8") as fh:
                content = fh.read()
            lines = content.splitlines()
        except (OSError, UnicodeDecodeError):
            content = ""
            lines = []

        line_count = len(lines)
        import_count = _count_imports(lines)

        file_data.append(
            {
                "abs_path": abs_path,
                "rel_path": rel_path,
                "language": language,
                "line_count": line_count,
                "import_count": import_count,
                "content": content,
                "stem": stem,
            }
        )

        if stem not in stems:
            stems[stem] = []
        stems[stem].append(idx)

    # ------------------------------------------------------------------
    # Step 3 — Compute import graph weight
    # ------------------------------------------------------------------
    for idx, fdata in enumerate(file_data):
        stem = fdata["stem"]
        weight = 0
        for other_idx, other in enumerate(file_data):
            if other_idx == idx:
                continue
            if stem in other["content"]:
                weight += 1
        fdata["import_weight"] = weight

    # ------------------------------------------------------------------
    # Step 4 — Batch AI risk assessment (batches of 10)
    # ------------------------------------------------------------------
    ai_results: dict[int, dict] = {}
    batch_size = 10

    for batch_start in range(0, len(file_data), batch_size):
        batch = file_data[batch_start : batch_start + batch_size]
        numbered_entries: list[str] = []
        for local_idx, fdata in enumerate(batch):
            snippet = fdata["content"][:600]
            numbered_entries.append(
                f"{local_idx}. {fdata['rel_path']}\n{snippet}"
            )
        user_message = "\n\n---\n\n".join(numbered_entries)

        try:
            client = _get_client()
            logger.info(
                "Requesting risk assessment from OpenAI (model=%s, batch_start=%d, count=%d)",
                MODEL,
                batch_start,
                len(batch),
            )
            response = await client.chat.completions.create(
                model=MODEL,
                max_tokens=2048,
                messages=[
                    {"role": "system", "content": _RISK_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            )
            raw = response.choices[0].message.content or ""
            logger.debug("OpenAI risk assessment raw response: %s", raw[:500])
            parsed: list[dict] = json.loads(_extract_json(raw))
            for item in parsed:
                global_idx = batch_start + item["index"]
                ai_results[global_idx] = item
        except Exception as exc:
            logger.warning(
                "AI risk assessment failed for batch starting at %d: %s — using metric fallback",
                batch_start,
                exc,
            )

    # ------------------------------------------------------------------
    # Step 5 — Build result
    # ------------------------------------------------------------------
    focus_set = set(focus_paths)
    result_files: list[dict] = []

    for idx, fdata in enumerate(file_data):
        ai = ai_results.get(idx)
        if ai:
            risk_score = float(ai.get("risk_score", 0))
            risk_factors = ai.get("risk_factors", [])
            blast_radius = ai.get("blast_radius", "")
        else:
            risk_score = _metric_based_score(
                fdata["import_count"], fdata["line_count"], fdata["import_weight"]
            )
            risk_factors = []
            blast_radius = (
                f"Imported by {fdata['import_weight']} module(s)" if fdata["import_weight"] > 0 else "No direct imports detected"
            )

        result_files.append(
            {
                "path": fdata["abs_path"],
                "relative_path": fdata["rel_path"],
                "language": fdata["language"],
                "line_count": fdata["line_count"],
                "import_count": fdata["import_count"],
                "risk_score": round(risk_score, 2),
                "risk_factors": risk_factors,
                "blast_radius": blast_radius,
                "is_focus": fdata["abs_path"] in focus_set,
            }
        )

    result_files.sort(key=lambda f: f["risk_score"], reverse=True)

    logger.info(
        "Scan complete: %d files, highest risk=%.1f",
        len(result_files),
        result_files[0]["risk_score"] if result_files else 0.0,
    )

    return {
        "root": directory,
        "file_count": len(result_files),
        "files": result_files,
    }


async def generate_code_quiz(file_path: str, title: str) -> list[dict]:
    """Read a source file and generate 3–5 comprehension quiz questions via OpenAI.

    Returns a list of question dicts matching the standard quiz question schema.
    """
    try:
        with open(file_path, encoding="utf-8") as fh:
            file_contents = fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"Cannot read file at {file_path}: {exc}") from exc

    truncated = file_contents[:4000]
    user_message = f"File: {file_path}\n\n{truncated}"

    client = _get_client()
    logger.info(
        "Requesting code quiz generation from OpenAI (model=%s, file=%s)",
        MODEL,
        file_path,
    )

    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=2048,
        messages=[
            {"role": "system", "content": _CODE_QUIZ_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    raw = response.choices[0].message.content or ""
    logger.debug("OpenAI code quiz raw response: %s", raw[:500])

    try:
        questions: list[dict] = json.loads(_extract_json(raw))
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse OpenAI code quiz response as JSON: %s", exc)
        raise ValueError(f"OpenAI returned invalid JSON for code quiz: {exc}") from exc

    if not isinstance(questions, list) or len(questions) == 0:
        raise ValueError("OpenAI returned an empty or non-list code quiz response")

    logger.info("Generated %d code quiz questions for %s", len(questions), file_path)
    return questions
