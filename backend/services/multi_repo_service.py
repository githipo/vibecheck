import json
import logging
import os
import re

import openai
from dotenv import load_dotenv
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.session import Repo, RepoConnection, RepoGroup
from services.codebase_service import scan_directory

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


_MULTI_REPO_SYSTEM_PROMPT = """\
You are analyzing a multi-repo system. Your job is to find cross-repo connections by \
examining the top files from each repository.

Look for:
- API calls: frontend code fetching routes defined in backend
- Shared types: interface or type names appearing in multiple repos
- Package dependencies: one repo listing another as a dependency (package.json, pyproject.toml)
- Events: event names or message types shared across repos

Return ONLY a JSON object with this exact shape:
{
  "summary": "2-3 sentence description of how all repos connect",
  "connections": [
    {
      "from_repo": "<repo name>",
      "to_repo": "<repo name>",
      "connection_type": "api_call | shared_type | package_dependency | event",
      "description": "Short human-readable description of the connection",
      "evidence": "file/path:linenum or code snippet showing the connection"
    }
  ],
  "repo_briefs": {
    "<repo name>": "One-sentence description of this repo's role"
  }
}

If no connections are found, return an empty connections array. Do not invent connections \
that are not supported by the file content provided.\
"""


async def analyze_group(group_id: int, db: AsyncSession) -> dict:
    """Load the RepoGroup + its Repos, scan each repo's top files, call the AI
    to detect cross-repo connections, persist the results, and return the analysis.

    Returns a dict matching the structure needed by RepoContextOut:
      {
        "group_name": str,
        "summary": str,
        "connections": list[dict],   # ORM objects, not dicts — caller converts
        "repo_briefs": dict[str, str],
      }
    """
    # ------------------------------------------------------------------
    # 1. Load group and repos
    # ------------------------------------------------------------------
    result = await db.execute(
        select(RepoGroup)
        .where(RepoGroup.id == group_id)
        .options(selectinload(RepoGroup.repos))
    )
    group: RepoGroup | None = result.scalar_one_or_none()

    if group is None:
        raise ValueError(f"RepoGroup {group_id} not found")

    repos: list[Repo] = list(group.repos)
    if not repos:
        raise ValueError(f"RepoGroup {group_id} has no repos to analyze")

    logger.info(
        "Starting multi-repo analysis for group id=%d name=%r (%d repos)",
        group_id,
        group.name,
        len(repos),
    )

    # ------------------------------------------------------------------
    # 2. For each repo, scan top files and read snippets
    # ------------------------------------------------------------------
    repo_file_sections: list[str] = []

    for repo in repos:
        if not os.path.isdir(repo.path):
            logger.warning(
                "Repo %r path does not exist or is not a directory: %s — skipping",
                repo.name,
                repo.path,
            )
            repo_file_sections.append(
                f"=== Repo: {repo.name} (role: {repo.role}) ===\n"
                f"[Path not accessible: {repo.path}]\n"
            )
            continue

        try:
            scan_result = await scan_directory(
                directory=repo.path,
                extensions=[".py", ".ts", ".tsx", ".js", ".go", ".rs", ".java", ".json", ".toml"],
                max_files=20,
                focus_paths=[],
            )
        except Exception as exc:
            logger.warning(
                "Scan failed for repo %r at %s: %s — skipping",
                repo.name,
                repo.path,
                exc,
            )
            repo_file_sections.append(
                f"=== Repo: {repo.name} (role: {repo.role}) ===\n"
                f"[Scan failed: {exc}]\n"
            )
            continue

        top_files = scan_result["files"][:5]
        lines: list[str] = [f"=== Repo: {repo.name} (role: {repo.role}, path: {repo.path}) ==="]

        for file_info in top_files:
            file_path: str = file_info["path"]
            rel_path: str = file_info["relative_path"]
            try:
                with open(file_path, encoding="utf-8") as fh:
                    snippet = fh.read(400)
            except (OSError, UnicodeDecodeError):
                snippet = "[unreadable]"
            lines.append(f"--- {rel_path} ---")
            lines.append(snippet)
            lines.append("")

        repo_file_sections.append("\n".join(lines))

    user_message = "\n\n".join(repo_file_sections)

    # ------------------------------------------------------------------
    # 3. Call OpenAI
    # ------------------------------------------------------------------
    client = _get_client()
    logger.info(
        "Requesting multi-repo connection analysis from OpenAI (model=%s, group=%d)",
        MODEL,
        group_id,
    )

    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": _MULTI_REPO_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    raw = response.choices[0].message.content or ""
    logger.debug("OpenAI multi-repo analysis raw response: %s", raw[:800])

    try:
        ai_result: dict = json.loads(_extract_json(raw))
    except json.JSONDecodeError as exc:
        logger.error(
            "Failed to parse OpenAI multi-repo response as JSON: %s — raw: %s",
            exc,
            raw[:300],
        )
        raise ValueError(f"OpenAI returned invalid JSON for multi-repo analysis: {exc}") from exc

    summary: str = ai_result.get("summary", "")
    ai_connections: list[dict] = ai_result.get("connections", [])
    repo_briefs: dict[str, str] = ai_result.get("repo_briefs", {})

    # ------------------------------------------------------------------
    # 4. Build a name -> Repo map for resolving repo names to IDs
    # ------------------------------------------------------------------
    repo_name_map: dict[str, Repo] = {r.name: r for r in repos}

    # ------------------------------------------------------------------
    # 5. Clear old connections for this group and persist new ones
    # ------------------------------------------------------------------
    await db.execute(
        delete(RepoConnection).where(RepoConnection.group_id == group_id)
    )

    saved_connections: list[RepoConnection] = []
    for conn in ai_connections:
        from_name: str = conn.get("from_repo", "")
        to_name: str = conn.get("to_repo", "")
        from_repo = repo_name_map.get(from_name)
        to_repo = repo_name_map.get(to_name)

        if from_repo is None or to_repo is None:
            logger.warning(
                "Skipping connection with unrecognized repo names: from=%r to=%r",
                from_name,
                to_name,
            )
            continue

        connection = RepoConnection(
            group_id=group_id,
            from_repo_id=from_repo.id,
            to_repo_id=to_repo.id,
            connection_type=conn.get("connection_type", "other"),
            description=conn.get("description", ""),
            evidence=conn.get("evidence", ""),
        )
        db.add(connection)
        saved_connections.append(connection)

    await db.commit()

    for conn in saved_connections:
        await db.refresh(conn)

    logger.info(
        "Multi-repo analysis complete: group=%d, connections=%d",
        group_id,
        len(saved_connections),
    )

    return {
        "group_name": group.name,
        "summary": summary,
        "connections": saved_connections,
        "repo_briefs": repo_briefs,
    }
