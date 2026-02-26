# VibeCheck — Project Intelligence

Living document. Updated as the project evolves. Tracks decisions, patterns, gotchas, and current state so any new Claude session starts with full context.

---

## What exists right now

### Data models
| Model | Purpose |
|---|---|
| `Session` | A unit of work — transcript + metadata. source_type includes `code_file` for code-first quizzes |
| `Quiz` | AI-generated questions linked to a Session |
| `Attempt` | User's answers + AI evaluations + score |
| `Insight` | Extracted decisions/patterns/gotchas from a Session transcript |
| `FocusArea` | User-pinned files or concepts, used to weight scans and analytics |

### API surface
```
/api/sessions             CRUD
/api/sessions/{id}/quiz   generate + fetch
/api/sessions/{id}/attempt + /results
/api/sessions/{id}/insights + /insights/apply
/api/analytics            + /analytics/catchup
/api/codebase/scan        + /codebase/quiz
/api/focus                CRUD
```

### Frontend pages
| Route | Page |
|---|---|
| `/` | Home — session list |
| `/sessions/new` | Paste transcript |
| `/sessions/:id` | Session detail + actions |
| `/sessions/:id/quiz` | Step-through quiz |
| `/sessions/:id/results` | Score + feedback |
| `/sessions/:id/insights` | Decisions/patterns/gotchas + CLAUDE.md apply |
| `/analytics` | Comprehension dashboard + blind spots + catch-up briefs |
| `/codebase` | Codebase scanner + focus areas + code-first quiz trigger |

### MCP tools (available in all Claude Code sessions)
| Tool | What it does |
|---|---|
| `vibecheck_capture` | Package current session → create + quiz |
| `vibecheck_sessions` | List recent sessions |
| `vibecheck_results` | Get results for a session |
| `vibecheck_insights` | Extract insights from a session |
| `vibecheck_blind_spots` | Cross-session comprehension analytics |
| `vibecheck_catchup` | Personalized catch-up brief for a weak topic |
| `vibecheck_scan` | Scan directory for comprehension risk |
| `vibecheck_code_quiz` | Generate quiz from a code file |

---

## Architectural decisions

### AI provider: OpenAI gpt-4o (not Claude)
Switched from Anthropic SDK at setup time — account had no credits. All AI logic is isolated in `services/claude_service.py`. To switch back to Claude: change env var, swap one pip package, rewrite that one file. Nothing else touches the provider.

### Code-first quizzing reuses Session/Quiz/Attempt pipeline
Rather than a separate quiz type, code-file sessions use `source_type = "code_file"` and store file contents as the transcript. This means the full quiz/attempt/results flow works unchanged — only the generation step differs (reads a file instead of a conversation).

### Analytics topic clustering is computed, not stored
Topic labels are generated per-request via a batch OpenAI call. Not stored in DB. This keeps the schema simple at the cost of a ~2s overhead on the analytics endpoint. If this becomes slow, the classification should be cached.

### Codebase scan is stateless
Scan results are not persisted. Each scan is a fresh API call. FocusAreas are stored but scan output is not — intentionally, since file contents change.

### MCP server is a thin HTTP client
The MCP server (`backend/mcp_server.py`) only makes HTTP calls to the local FastAPI backend. It contains no business logic. This means the backend must be running for any MCP tool to work.

---

## Patterns established

- **Services are plain async functions** — no classes. One file per domain (`claude_service`, `analytics_service`, `codebase_service`, `insights_service`, `quiz_engine`).
- **Routers are thin** — validation + DB load + service call + return. No business logic in routers.
- **All AI provider calls use a lazy singleton client** — `_get_client()` pattern, loads API key from env on first call.
- **JSON fields use `_extract_json()`** — strips markdown fences before parsing, since models sometimes wrap JSON in ` ```json ` blocks.
- **Frontend API calls live only in `src/api/sessions.ts`** — never `fetch()` directly from components.
- **Error handling in MCP tools returns strings, never raises** — a broken MCP tool must not crash Claude Code.

---

## Gotchas & constraints

- **Backend must be running on port 8000** for MCP tools and Stop hook to work. If it's down, the hook silently no-ops (by design).
- **Stop hook fires at end of every Claude Code agent run**, not just end of session. Short runs (<4 turns) are filtered out. Long multi-topic sessions produce a single merged capture.
- **Codebase scan caps at 50 files** — scans larger directories by taking the largest files first. Small utility files get deprioritised.
- **Insights endpoint returns 409** if insights already exist for a session. The frontend and MCP tool both handle this by falling back to GET.
- **`analytics_service.py` recomputes topic classification on every call** — if a user has many sessions with many questions, this gets slow. Watch this.
- **File path validation in `/insights/apply`** — must be absolute, must exist, must end in `.md`. The backend writes directly to disk; no undo.
- **`source_type = "code_file"` sessions** have file contents as transcript — can be large. No truncation at the session level, but quiz generation truncates to 4000 chars.

---

## What's NOT built yet
- No auth — single user, no accounts
- No git integration — codebase scanner doesn't know which files Claude touched vs. which were pre-existing
- Analytics topic classification not cached — will slow down with scale
- No way to retake a quiz and compare scores over time for the same session
- No way to retake a quiz and compare scores over time for the same session (retake works but scores aren't diff'd)
- Codebase scan results not persisted — no historical risk trend across scans
