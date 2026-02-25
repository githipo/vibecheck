#!/usr/bin/env python3
"""
VibeCheck Stop hook — automatically captures Claude Code sessions.
Receives session data as JSON on stdin (Claude Code Stop event).
Silently no-ops if VibeCheck backend is not running.
"""

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime


def extract_text_from_content(content: object) -> str:
    """Extract plain text from a message's content field.

    Content can be a plain string or a list of content blocks.
    Only 'text' typed blocks are extracted; tool_use, tool_result, etc. are skipped.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                if text:
                    parts.append(text)
        return "\n".join(parts)
    return ""


def has_meaningful_text(content: object) -> bool:
    """Return True if a message's content contains any non-empty text."""
    return bool(extract_text_from_content(content).strip())


def format_transcript(messages: list) -> str:
    """Format a list of message dicts into a readable plain-text transcript."""
    lines = []
    for message in messages:
        role = message.get("role", "")
        content = message.get("content", "")

        if role == "user":
            prefix = "USER: "
        elif role == "assistant":
            prefix = "ASSISTANT: "
        else:
            continue

        text = extract_text_from_content(content)
        if not text.strip():
            continue

        # Truncate individual messages to avoid massive transcripts
        if len(text) > 3000:
            text = text[:3000] + "... [truncated]"

        lines.append(prefix + text)

    return "\n\n".join(lines)


def build_title() -> str:
    """Build a human-readable session title from the current directory and time."""
    dirname = os.path.basename(os.getcwd())
    date_str = datetime.now().strftime("%b %-d %H:%M")
    return f"{dirname} — {date_str}"


def main() -> None:
    # Step 1: Read and parse JSON from stdin
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw)
    except Exception:
        sys.exit(0)

    # Step 2: Extract transcript; exit silently if missing or empty
    transcript = payload.get("transcript")
    if not transcript or not isinstance(transcript, list):
        sys.exit(0)

    # Step 3: Count meaningful turns; skip if fewer than 4
    meaningful_turns = sum(
        1
        for msg in transcript
        if msg.get("role") in ("user", "assistant")
        and has_meaningful_text(msg.get("content", ""))
    )
    if meaningful_turns < 4:
        sys.exit(0)

    # Step 4: Format transcript as readable plain text
    transcript_text = format_transcript(transcript)
    if not transcript_text.strip():
        sys.exit(0)

    # Step 5: Build title
    title = build_title()

    # Steps 6-8: POST to VibeCheck API and open browser — wrapped in silent try/except
    try:
        # POST session to VibeCheck
        request_payload = json.dumps({
            "title": title,
            "transcript": transcript_text,
            "source_type": "claude_code",
        }).encode()

        req = urllib.request.Request(
            "http://localhost:8000/api/sessions",
            data=request_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=5) as resp:
            session = json.loads(resp.read())
            session_id = session["id"]

        # Open browser to session detail page
        subprocess.Popen(["open", f"http://localhost:5173/sessions/{session_id}"])

    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
