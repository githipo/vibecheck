import logging
import os

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = logging.getLogger(__name__)

BASE_URL = os.getenv("VIBECHECK_API_URL", "http://localhost:8000")

mcp = FastMCP(
    "vibecheck",
    instructions="VibeCheck verifies that you understand what was built in your AI coding sessions. Use vibecheck_capture to quiz yourself on any session.",
)


@mcp.tool()
async def vibecheck_capture(
    title: str,
    transcript: str,
    source_type: str = "claude_code",
) -> str:
    """Capture this AI coding session in VibeCheck and generate a comprehension quiz. Call this when the user asks to be quizzed on what was just built. Provide the session title and a full plain-text transcript of what was discussed and built."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            create_resp = await client.post(
                f"{BASE_URL}/api/sessions",
                json={"title": title, "transcript": transcript, "source_type": source_type},
            )
            create_resp.raise_for_status()
            session = create_resp.json()
            session_id: int = session["id"]

            quiz_resp = await client.post(
                f"{BASE_URL}/api/sessions/{session_id}/quiz",
                json={},
            )
            quiz_resp.raise_for_status()

        return (
            f"Quiz ready! Open http://localhost:5173/sessions/{session_id}/quiz to take it.\n\n"
            f"Session title: {title}\n"
            f"Session ID: {session_id}"
        )
    except httpx.HTTPError as exc:
        logger.error("HTTP error during vibecheck_capture: %s", exc)
        return f"Could not reach the VibeCheck API. Is the backend running at {BASE_URL}? (Error: {exc})"
    except Exception as exc:
        logger.error("Unexpected error during vibecheck_capture: %s", exc)
        return f"An unexpected error occurred while capturing the session: {exc}"


@mcp.tool()
async def vibecheck_sessions() -> str:
    """List recent VibeCheck sessions and their status."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(f"{BASE_URL}/api/sessions")
            resp.raise_for_status()
            sessions: list[dict] = resp.json()

        if not sessions:
            return "No sessions yet. Use vibecheck_capture to create one."

        lines = ["Recent VibeCheck sessions:", ""]
        for s in sessions:
            session_id = s["id"]
            session_title = s["title"]
            source_type = s["source_type"]
            status = s["status"]
            created_at_raw: str = s["created_at"]
            try:
                from datetime import datetime, timezone

                dt = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
                formatted_date = dt.astimezone(timezone.utc).strftime("%b %d %H:%M")
            except Exception:
                formatted_date = created_at_raw

            lines.append(
                f"#{session_id} — {session_title} ({source_type}) [{status}] — {formatted_date}"
            )

        return "\n".join(lines)
    except httpx.HTTPError as exc:
        logger.error("HTTP error during vibecheck_sessions: %s", exc)
        return f"Could not reach the VibeCheck API. Is the backend running at {BASE_URL}? (Error: {exc})"
    except Exception as exc:
        logger.error("Unexpected error during vibecheck_sessions: %s", exc)
        return f"An unexpected error occurred while listing sessions: {exc}"


@mcp.tool()
async def vibecheck_results(session_id: int) -> str:
    """Get the latest quiz results for a VibeCheck session."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(f"{BASE_URL}/api/sessions/{session_id}/results")

            if resp.status_code == 404:
                return f"No results found for session {session_id}. Has the quiz been taken yet?"

            resp.raise_for_status()
            attempt: dict = resp.json()

        overall_score = round(attempt["score"])
        feedback_summary = attempt["feedback_summary"]
        evaluations: list[dict] = attempt["evaluations"]

        verdict_symbols = {
            "correct": "✓",
            "partial": "~",
            "incorrect": "✗",
        }

        lines = [
            f"Session #{session_id} Results — Score: {overall_score}/100",
            "",
            f"Overall: {feedback_summary}",
            "",
        ]

        for i, ev in enumerate(evaluations, start=1):
            question_id = ev["question_id"]
            verdict = ev["verdict"]
            score = ev["score"]
            feedback = ev["feedback"]
            symbol = verdict_symbols.get(verdict, "?")
            label = f"q{question_id}" if str(question_id).isdigit() else str(question_id)
            # Truncate feedback to first sentence for the one-liner
            one_liner = feedback.split(".")[0].strip()
            lines.append(f"{label} {symbol} {verdict} ({score}): {one_liner}.")

        return "\n".join(lines)
    except httpx.HTTPError as exc:
        logger.error("HTTP error during vibecheck_results for session %d: %s", session_id, exc)
        return f"Could not reach the VibeCheck API. Is the backend running at {BASE_URL}? (Error: {exc})"
    except Exception as exc:
        logger.error(
            "Unexpected error during vibecheck_results for session %d: %s", session_id, exc
        )
        return f"An unexpected error occurred while fetching results for session {session_id}: {exc}"


@mcp.tool()
async def vibecheck_insights(session_id: int) -> str:
    """
    Generate and return Session Intelligence for a VibeCheck session.
    Extracts architectural decisions, patterns, gotchas, and proposed CLAUDE.md rules from the session transcript.
    Call this after vibecheck_capture to get structured project intelligence.
    """
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            post_resp = await client.post(
                f"{BASE_URL}/api/sessions/{session_id}/insights",
                json={},
            )

            if post_resp.status_code == 409:
                get_resp = await client.get(
                    f"{BASE_URL}/api/sessions/{session_id}/insights"
                )
                get_resp.raise_for_status()
                data: dict = get_resp.json()
            else:
                post_resp.raise_for_status()
                data = post_resp.json()

        decisions: list[dict] = data.get("decisions", [])
        patterns: list[dict] = data.get("patterns", [])
        gotchas: list[dict] = data.get("gotchas", [])
        proposed_rules: list[dict] = data.get("proposed_rules", [])

        session_title = f"Session #{session_id}"
        try:
            get_session_resp = await client.get(
                f"{BASE_URL}/api/sessions/{session_id}"
            )
            if get_session_resp.status_code == 200:
                session_title = get_session_resp.json().get("title", session_title)
        except Exception:
            pass

        lines = [f"Session Intelligence — {session_title}", ""]

        if decisions:
            lines.append("DECISIONS MADE")
            for d in decisions:
                rejected = ", ".join(d.get("alternatives_rejected", [])) or "none noted"
                lines.append(f"• {d['decision']}: {d['rationale']}")
                lines.append(f"  Rejected: {rejected}")
            lines.append("")

        if patterns:
            lines.append("PATTERNS ESTABLISHED")
            for p in patterns:
                lines.append(f"• {p['pattern']}: {p['description']}")
            lines.append("")

        if gotchas:
            lines.append("GOTCHAS & CONSTRAINTS")
            for g in gotchas:
                lines.append(f"• {g['issue']}: {g['context']}")
            lines.append("")

        if proposed_rules:
            lines.append("PROPOSED CLAUDE.MD ADDITIONS")
            for r in proposed_rules:
                lines.append(f"[{r['section']}] {r['rule']}")
                lines.append(f"  Why: {r['rationale']}")
            lines.append("")

        lines.append(
            f"To apply these to a CLAUDE.md file, open:\n"
            f"http://localhost:5173/sessions/{session_id}/insights"
        )

        return "\n".join(lines)
    except httpx.HTTPError as exc:
        logger.error(
            "HTTP error during vibecheck_insights for session %d: %s", session_id, exc
        )
        return f"Could not reach the VibeCheck API. Is the backend running at {BASE_URL}? (Error: {exc})"
    except Exception as exc:
        logger.error(
            "Unexpected error during vibecheck_insights for session %d: %s",
            session_id,
            exc,
        )
        return f"An unexpected error occurred while fetching insights for session {session_id}: {exc}"


@mcp.tool()
async def vibecheck_blind_spots() -> str:
    """
    Show your comprehension analytics and blind spots across all VibeCheck sessions.
    Returns topic scores, identifies weak areas, and overall learning trends.
    """
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(f"{BASE_URL}/api/analytics")
            resp.raise_for_status()
            data: dict = resp.json()

        if data["total_questions_answered"] == 0:
            return "No quiz attempts yet. Complete some quizzes first."

        overall_avg: float = data["overall_avg_score"]
        total_q: int = data["total_questions_answered"]
        completed: int = data["completed_sessions"]
        topic_scores: list[dict] = data["topic_scores"]
        blind_spots: list[dict] = data["blind_spots"]

        # Sort topics: blind spots first, then by avg_score ascending
        topic_scores_sorted = sorted(
            topic_scores, key=lambda t: (not t["is_blind_spot"], t["avg_score"])
        )

        def _symbol(avg: float) -> str:
            if avg >= 70:
                return "✓"
            if avg >= 50:
                return "~"
            return "✗"

        lines = [
            "COMPREHENSION ANALYTICS",
            "",
            f"Overall: {overall_avg:.0f}/100 across {total_q} questions in {completed} sessions",
            "",
            "TOPIC BREAKDOWN",
        ]

        for t in topic_scores_sorted:
            sym = _symbol(t["avg_score"])
            blind_tag = "  ← BLIND SPOT" if t["is_blind_spot"] else ""
            name = t["topic"].ljust(22)
            lines.append(
                f"{sym} {name} {t['avg_score']:.0f}/100  ({t['question_count']} questions){blind_tag}"
            )

        if blind_spots:
            weak_names = ", ".join(b["topic"] for b in blind_spots)
            lines += [
                "",
                "BLIND SPOTS (avg < 60%, 2+ questions)",
                f"Your weak areas: {weak_names}",
                "",
                f'Run vibecheck_catchup("{blind_spots[0]["topic"]}") to get a personalized explanation.',
            ]
        else:
            lines += [
                "",
                "No blind spots found — keep it up!",
            ]

        lines.append(
            "Or open http://localhost:5173/analytics for the full dashboard."
        )

        return "\n".join(lines)
    except httpx.HTTPError as exc:
        logger.error("HTTP error during vibecheck_blind_spots: %s", exc)
        return f"Could not reach the VibeCheck API. Is the backend running at {BASE_URL}? (Error: {exc})"
    except Exception as exc:
        logger.error("Unexpected error during vibecheck_blind_spots: %s", exc)
        return f"An unexpected error occurred while fetching analytics: {exc}"


@mcp.tool()
async def vibecheck_catchup(topic: str) -> str:
    """
    Generate a personalized catch-up explanation for a topic you've struggled with.
    Based on your actual wrong answers and the transcripts of sessions you worked on.
    topic should be one of your blind spots from vibecheck_blind_spots().
    """
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{BASE_URL}/api/analytics/catchup",
                json={"topic": topic},
            )
            resp.raise_for_status()
            data: dict = resp.json()

        brief: str = data.get("brief", "")
        return f"CATCH-UP BRIEF: {topic}\n\n{brief}"
    except httpx.HTTPError as exc:
        logger.error(
            "HTTP error during vibecheck_catchup for topic %r: %s", topic, exc
        )
        return f"Could not reach the VibeCheck API. Is the backend running at {BASE_URL}? (Error: {exc})"
    except Exception as exc:
        logger.error(
            "Unexpected error during vibecheck_catchup for topic %r: %s", topic, exc
        )
        return f"An unexpected error occurred while generating catch-up brief for '{topic}': {exc}"


@mcp.tool()
async def vibecheck_scan(directory: str) -> str:
    """Scan a code directory for comprehension risk. Returns files ranked by how likely a developer is to misunderstand them, with AI-assessed risk scores and blast radius notes."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{BASE_URL}/api/codebase/scan",
                json={"directory": directory},
            )
            resp.raise_for_status()
            data: dict = resp.json()

        root: str = data.get("root", directory)
        file_count: int = data.get("file_count", 0)
        files: list[dict] = data.get("files", [])
        top_files = files[:10]

        lines = [
            "CODEBASE COMPREHENSION RISK SCAN",
            f"Directory: {root}",
            f"{file_count} files scanned",
            "",
            "HIGHEST RISK FILES",
        ]

        for f in top_files:
            score = int(round(f.get("risk_score", 0)))
            rel = f.get("relative_path", f.get("path", ""))
            blast = f.get("blast_radius", "")
            factors: list[str] = f.get("risk_factors", [])
            is_focus: bool = f.get("is_focus", False)
            prefix = "🎯" if is_focus else "  "
            factors_str = ", ".join(factors) if factors else "No specific factors"
            lines.append(f"[{score:3d}] {prefix} {rel} — \"{blast}\"")
            lines.append(f"       Risk factors: {factors_str}")

        lines.append("")
        lines.append("Use vibecheck_code_quiz(\"/abs/path/to/file.py\") to quiz yourself on any file.")
        lines.append(f"Full map: http://localhost:5173/codebase")

        return "\n".join(lines)
    except httpx.HTTPError as exc:
        logger.error("HTTP error during vibecheck_scan: %s", exc)
        return f"Could not reach the VibeCheck API. Is the backend running at {BASE_URL}? (Error: {exc})"
    except Exception as exc:
        logger.error("Unexpected error during vibecheck_scan: %s", exc)
        return f"An unexpected error occurred while scanning {directory}: {exc}"


@mcp.tool()
async def vibecheck_code_quiz(file_path: str) -> str:
    """Generate and start a comprehension quiz directly from a source code file. No session transcript needed — VibeCheck reads the file and quizzes you on what it does and why."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{BASE_URL}/api/codebase/quiz",
                json={"file_path": file_path},
            )
            resp.raise_for_status()
            session: dict = resp.json()

        session_id: int = session["id"]
        filename = os.path.basename(file_path)

        return (
            f"Quiz ready for {filename}!\n\n"
            f"Take it at: http://localhost:5173/sessions/{session_id}/quiz\n\n"
            f"Session ID: {session_id}"
        )
    except httpx.HTTPError as exc:
        logger.error("HTTP error during vibecheck_code_quiz for %s: %s", file_path, exc)
        return f"Could not reach the VibeCheck API. Is the backend running at {BASE_URL}? (Error: {exc})"
    except Exception as exc:
        logger.error("Unexpected error during vibecheck_code_quiz for %s: %s", file_path, exc)
        return f"An unexpected error occurred while generating code quiz for '{file_path}': {exc}"


@mcp.tool()
async def vibecheck_self_brief(directory: str) -> str:
    """Generate an AI onboarding brief for a codebase directory. Analyzes the most complex files and produces: architecture summary, non-obvious conventions, critical invariants, common AI mistakes to avoid, and suggested custom sub-agents with pre-written system prompts. Apply the result to your CLAUDE.md to make future sessions smarter."""
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{BASE_URL}/api/codebase/brief",
                json={"directory": directory},
            )
            resp.raise_for_status()
            data: dict = resp.json()

        brief: dict = data.get("brief", {})
        suggested_agents: list[dict] = data.get("suggested_agents", [])

        architecture_summary: str = brief.get("architecture_summary", "")
        non_obvious_conventions: list[str] = brief.get("non_obvious_conventions", [])
        critical_invariants: list[str] = brief.get("critical_invariants", [])
        common_mistakes: list[str] = brief.get("common_mistakes_to_avoid", [])
        key_entry_points: list[dict] = brief.get("key_entry_points", [])

        lines = [
            f"AI ONBOARDING BRIEF — {directory}",
            "",
            "ARCHITECTURE",
            architecture_summary,
            "",
            "NON-OBVIOUS CONVENTIONS",
        ]
        for convention in non_obvious_conventions:
            lines.append(f"• {convention}")

        lines.append("")
        lines.append("CRITICAL INVARIANTS")
        for invariant in critical_invariants:
            lines.append(f"• {invariant}")

        lines.append("")
        lines.append("COMMON AI MISTAKES TO AVOID")
        for mistake in common_mistakes:
            lines.append(f"✗ {mistake}")

        lines.append("")
        lines.append("KEY ENTRY POINTS")
        for entry in key_entry_points:
            lines.append(f"→ {entry.get('file', '')}: {entry.get('role', '')}")

        lines.append("")
        lines.append(f"SUGGESTED SUB-AGENTS ({len(suggested_agents)} agents)")
        for agent in suggested_agents:
            lines.append(f"[{agent.get('name', '')}] {agent.get('role', '')}")
            lines.append(f"  {agent.get('description', '')}")

        lines.append("")
        lines.append("To apply this brief + sub-agents to your CLAUDE.md:")
        lines.append("http://localhost:5173/codebase/brief")
        lines.append("")
        lines.append('Or paste your CLAUDE.md path and call vibecheck_apply_brief("/path/to/CLAUDE.md")')

        return "\n".join(lines)
    except httpx.HTTPError as exc:
        logger.error("HTTP error during vibecheck_self_brief for %s: %s", directory, exc)
        return f"Could not reach the VibeCheck API. Is the backend running at {BASE_URL}? (Error: {exc})"
    except Exception as exc:
        logger.error("Unexpected error during vibecheck_self_brief for %s: %s", directory, exc)
        return f"An unexpected error occurred while generating self-brief for '{directory}': {exc}"


@mcp.tool()
async def vibecheck_apply_brief(claude_md_path: str, directory: str) -> str:
    """Apply a generated AI brief and sub-agent definitions to a CLAUDE.md file. Generates the brief from directory and appends it to the specified CLAUDE.md."""
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            brief_resp = await client.post(
                f"{BASE_URL}/api/codebase/brief",
                json={"directory": directory},
            )
            brief_resp.raise_for_status()
            brief_data: dict = brief_resp.json()

            apply_resp = await client.post(
                f"{BASE_URL}/api/codebase/brief/apply",
                json={
                    "file_path": claude_md_path,
                    "brief": brief_data["brief"],
                    "suggested_agents": brief_data.get("suggested_agents", []),
                    "include_agents": True,
                },
            )
            apply_resp.raise_for_status()
            result: dict = apply_resp.json()

        chars_added: int = result.get("chars_added", 0)
        return (
            f"AI onboarding brief applied to {claude_md_path}\n"
            f"{chars_added} characters added.\n\n"
            f"The brief includes:\n"
            f"• Architecture summary\n"
            f"• Non-obvious conventions\n"
            f"• Critical invariants\n"
            f"• Common AI mistakes to avoid\n"
            f"• Key entry points\n"
            f"• {len(brief_data.get('suggested_agents', []))} suggested sub-agents\n\n"
            f"Your CLAUDE.md is now ready for future AI sessions."
        )
    except httpx.HTTPError as exc:
        logger.error(
            "HTTP error during vibecheck_apply_brief for %s: %s", claude_md_path, exc
        )
        return f"Could not reach the VibeCheck API. Is the backend running at {BASE_URL}? (Error: {exc})"
    except Exception as exc:
        logger.error(
            "Unexpected error during vibecheck_apply_brief for %s: %s", claude_md_path, exc
        )
        return f"An unexpected error occurred while applying brief to '{claude_md_path}': {exc}"


@mcp.tool()
async def vibecheck_repo_context(group_name: str) -> str:
    """Get cross-repo relationship context for a multi-repo group. Surfaces how repos connect (API calls, shared types, package deps) so you can understand the full system when working in one repo. Run vibecheck_repo_context("my-system") to see all connections."""
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            # 1. List all groups and find the one matching group_name
            list_resp = await client.get(f"{BASE_URL}/api/repos/groups")
            list_resp.raise_for_status()
            groups: list[dict] = list_resp.json()

            matched: dict | None = None
            for g in groups:
                if g.get("name", "").lower() == group_name.lower():
                    matched = g
                    break

            if matched is None:
                known = ", ".join(f'"{g["name"]}"' for g in groups) or "none"
                return (
                    f"No repo group named \"{group_name}\" found.\n"
                    f"Known groups: {known}\n\n"
                    f"Create one via POST /api/repos/groups or the VibeCheck UI."
                )

            group_id: int = matched["id"]

            # 2. Trigger AI analysis (this may take a while)
            analyze_resp = await client.post(
                f"{BASE_URL}/api/repos/groups/{group_id}/analyze"
            )
            analyze_resp.raise_for_status()

            # 3. Fetch context
            ctx_resp = await client.get(
                f"{BASE_URL}/api/repos/groups/{group_id}/context"
            )
            ctx_resp.raise_for_status()
            ctx: dict = ctx_resp.json()

        group_name_out: str = ctx.get("group_name", group_name)
        summary: str = ctx.get("summary", "")
        connections: list[dict] = ctx.get("connections", [])
        repo_briefs: dict[str, str] = ctx.get("repo_briefs", {})

        lines = [
            f"MULTI-REPO CONTEXT — {group_name_out}",
            "",
            "SUMMARY",
            summary,
            "",
        ]

        if repo_briefs:
            lines.append("REPOS")
            for name, brief in repo_briefs.items():
                lines.append(f"  {name}: {brief}")
            lines.append("")

        if connections:
            lines.append(f"CROSS-REPO CONNECTIONS ({len(connections)} found)")
            for conn in connections:
                conn_type = conn.get("connection_type", "unknown")
                description = conn.get("description", "")
                evidence = conn.get("evidence", "")
                evidence_str = f" [{evidence}]" if evidence else ""
                lines.append(f"  [{conn_type}] {description}{evidence_str}")
        else:
            lines.append("No cross-repo connections detected.")

        return "\n".join(lines)
    except httpx.HTTPError as exc:
        logger.error("HTTP error during vibecheck_repo_context for %r: %s", group_name, exc)
        return f"Could not reach the VibeCheck API. Is the backend running at {BASE_URL}? (Error: {exc})"
    except Exception as exc:
        logger.error("Unexpected error during vibecheck_repo_context for %r: %s", group_name, exc)
        return f"An unexpected error occurred while fetching repo context for '{group_name}': {exc}"


if __name__ == "__main__":
    mcp.run()
