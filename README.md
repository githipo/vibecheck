# VibeCheck

A learning-verification companion for AI-assisted development. VibeCheck watches your coding sessions and quizzes you to prove you understand what was built — not just that it works.

---

## What it does

| Feature | Description |
|---|---|
| **Session Quiz** | Paste a transcript → AI generates questions specific to your session → scored results with feedback |
| **Session Intelligence** | Extracts decisions, patterns, and gotchas from a session → proposes CLAUDE.md additions |
| **Comprehension Analytics** | Tracks your scores across all sessions by topic → identifies blind spots → generates personalized catch-up explanations |
| **Codebase Scanner** | Points at any directory → AI ranks files by comprehension risk → quiz yourself on any file directly |
| **Focus Areas** | Pin files or concepts you care about most — highlighted in every scan |
| **Code-First Quizzing** | Generate a quiz from a source file with no transcript needed |
| **AI Self-Brief** | Points Claude at your codebase → AI reads the riskiest files → generates a CLAUDE.md-ready onboarding brief with architecture notes, conventions, invariants, and suggested sub-agents |
| **Multi-Repo Analysis** | Group multiple repos → AI maps cross-repo connections (API calls, shared types, package deps) → surfaces context for working across a system |

All features are available in the browser and via **MCP tools** directly inside Claude Code.

---

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js 18+ and npm
- An OpenAI API key (or see [Switching to Claude](#switching-to-the-claude-api))
- [Claude Code](https://claude.ai/code) — for MCP tools and auto-capture hook

---

## Setup

### 1. Clone

```bash
git clone <repo-url>
cd vibecheck
```

### 2. Create `.env`

```bash
cp .env.example .env
```

```env
OPENAI_API_KEY=sk-proj-...
DATABASE_URL=sqlite+aiosqlite:///./vibecheck.db
CORS_ORIGINS=http://localhost:5173
```

### 3. Install dependencies

```bash
cd backend && uv sync
cd ../frontend && npm install
```

---

## Running

```bash
# Terminal 1 — backend
cd backend && uv run uvicorn main:app --reload

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open **`http://localhost:5173`**.

---

## Claude Code integration

VibeCheck has first-class Claude Code support: an MCP server that gives Claude tools to interact with VibeCheck, and a Stop hook that auto-captures sessions.

### MCP Server

The MCP server makes VibeCheck available as tools inside every Claude Code session. You can ask Claude things like:
- *"Quiz me on what we just built"*
- *"What are my comprehension blind spots?"*
- *"Scan this directory for files I might not understand"*
- *"Generate a catch-up brief on security"*

**Register it once:**
```bash
claude mcp add vibecheck -s user -- uv --project /path/to/vibecheck/backend run python /path/to/vibecheck/backend/mcp_server.py
```

Replace `/path/to/vibecheck` with your actual path. `-s user` makes it available in every project, not just this one.

Restart Claude Code after registering.

**Available tools:**

| Tool | Usage |
|---|---|
| `vibecheck_capture` | Package the current session as a transcript, create a session, and generate a quiz. Returns a quiz URL. |
| `vibecheck_sessions` | List recent sessions with status. |
| `vibecheck_results` | Get score + per-question feedback for a session. |
| `vibecheck_insights` | Extract architectural decisions, patterns, and gotchas from a session. Proposes CLAUDE.md additions. |
| `vibecheck_blind_spots` | Show comprehension scores by topic across all sessions. Flags topics below 60%. |
| `vibecheck_catchup` | Generate a personalized explanation for a weak topic, using your actual wrong answers and session transcripts as context. |
| `vibecheck_scan` | Scan a directory and rank files by comprehension risk. |
| `vibecheck_code_quiz` | Generate a quiz from a source file directly — no transcript needed. |
| `vibecheck_self_brief` | Scan a directory → AI reads the highest-risk files → returns an onboarding brief (architecture, conventions, invariants, mistakes to avoid) plus 3–5 suggested sub-agents with ready-to-paste CLAUDE.md blocks. |
| `vibecheck_apply_brief` | Same as `vibecheck_self_brief` but appends the full brief directly to a specified CLAUDE.md file. |
| `vibecheck_repo_context` | Given a named repo group, return cross-repo connection context — which repos call each other, share types, or depend on each other. |

**Example Claude Code conversations:**

```
You: Quiz me on what we just built
Claude: [calls vibecheck_capture with session transcript]
        Quiz ready! http://localhost:5173/sessions/4/quiz

You: What are my blind spots?
Claude: [calls vibecheck_blind_spots]
        Security: 38/100 across 6 questions ← BLIND SPOT
        Authentication: 100/100

You: Give me a catch-up on Security
Claude: [calls vibecheck_catchup("Security")]
        In your FastAPI session, you missed that a weak SECRET_KEY allows...

You: Scan my backend for risky files
Claude: [calls vibecheck_scan("/path/to/project/backend")]
        [95] analytics_service.py — complex async DB ops, critical path
        [75] quiz_engine.py — external service dependency

You: Generate a self-brief for my codebase
Claude: [calls vibecheck_self_brief("/path/to/project")]
        Architecture: FastAPI backend with async SQLAlchemy, React frontend...
        Non-obvious conventions:
          - All DB writes go through services/, never directly in routers/
          - ...
        Suggested sub-agents:
          - db-agent: knows the async SQLAlchemy patterns and cascade rules
          - api-contracts-agent: knows all Pydantic schemas and endpoint contracts

You: Apply that brief to my CLAUDE.md
Claude: [calls vibecheck_apply_brief("/path/to/project/CLAUDE.md", "/path/to/project")]
        Brief appended to CLAUDE.md (3 sections, 2 sub-agent blocks)
```

---

### Stop Hook (auto-capture)

Automatically saves every Claude Code session to VibeCheck when it ends. No manual steps required.

**Add to `~/.claude/settings.json`:**

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/vibecheck/hooks/session_end.py"
          }
        ]
      }
    ]
  }
}
```

Replace `/path/to/vibecheck` with your actual path. Restart Claude Code after adding.

**Behaviour:**
- Fires at the end of every Claude Code session with 4+ turns
- Silently skips short or trivial sessions
- POSTs the transcript to your local backend
- Opens your browser to the session detail page
- Does nothing if the backend isn't running — never interrupts Claude Code

---

## Using the web UI

### Session Quiz flow
1. **Home** (`/`) → New Session
2. Paste your AI session transcript, pick a source type, give it a title
3. On the session page → Generate Quiz (takes ~5s)
4. Answer questions one at a time
5. Results show your score, per-answer feedback, and what to revisit

### Session Intelligence
On any session detail page → **Extract Insights**. Takes ~5–10s. Shows:
- Architectural decisions made + what was rejected
- Patterns and conventions established
- Gotchas and tradeoffs discovered
- Proposed CLAUDE.md additions — paste your file path and apply with one click

### Comprehension Analytics
**Analytics** (`/analytics`) — aggregates all your quiz attempts:
- Overall score trend across sessions
- Per-topic breakdown (Security, Async Patterns, API Design, etc.)
- Blind spots highlighted in amber — topics below 60% with 2+ questions
- **Generate Catch-up Brief** for any blind spot — AI writes a personalized explanation using your actual wrong answers and session transcripts

### Codebase Map
**Codebase Map** (`/codebase`):
1. Enter an absolute directory path → Scan
2. Files ranked by comprehension risk (0–100), with specific risk factors and blast radius
3. Pin any file as a Focus Area — persisted, highlighted in future scans
4. **Quiz me on this** on any file → generates a quiz from the code itself

### AI Self-Brief
**Self-Brief** (`/self-brief`) — lets Claude study your codebase so it can work in it more intelligently:
1. Enter an absolute directory path → Generate Brief
2. AI reads the 15 highest-risk files (first 800 chars each) and produces:
   - **Architecture summary** — how the pieces connect
   - **Non-obvious conventions** — implicit rules ALL code follows
   - **Critical invariants** — assumptions the code relies on that cause subtle bugs if violated
   - **Common AI mistakes to avoid** — specific gotchas for this codebase
   - **Key entry points** — the 3–6 most important files and their exact roles
3. **Suggested sub-agents** — 3–5 domain specialists (e.g. `db-agent`, `api-contracts-agent`) with ready-to-paste CLAUDE.md system prompt blocks
4. **Apply to CLAUDE.md** — paste your CLAUDE.md path and append the full brief in one click

The brief is designed to be pasted into CLAUDE.md so every future Claude Code session in that project starts with this context already loaded.

### Multi-Repo Analysis
**Multi-Repo** (`/multi-repo`) — for systems that span multiple repositories:
1. Create a group by naming it and adding repo paths with roles (e.g. `api-service`, `frontend`, `shared-lib`)
2. **Analyze** — AI scans all repos and identifies cross-repo connections:
   - API calls between services
   - Shared type definitions
   - Package dependencies
   - Event producers/consumers
3. Results surface which repos call each other and why — useful context when making a change that touches multiple repos

---

## Using from your phone

Both servers must be running with `--host 0.0.0.0` / `--host`:

```bash
# Backend
cd backend && uv run uvicorn main:app --host 0.0.0.0 --reload

# Frontend
cd frontend && npm run dev -- --host
```

Add your Mac's local IP to `CORS_ORIGINS` in `.env`:
```env
CORS_ORIGINS=http://localhost:5173,http://192.168.x.x:5173
```

Find your IP: `ipconfig getifaddr en0`

Then open `http://192.168.x.x:5173` on your phone.

---

## Switching to the Claude API

Currently uses OpenAI (GPT-4o). To switch to Anthropic Claude, three changes:

**1. `.env`**
```env
# Remove: OPENAI_API_KEY=...
ANTHROPIC_API_KEY=sk-ant-...
```

**2. `backend/pyproject.toml`**
```toml
# Remove: "openai>=1.30",
# Add:    "anthropic>=0.25",
```
Then `uv sync`.

**3. `backend/services/claude_service.py`** — the only file with provider logic. Rewrite to use Anthropic SDK:

| | OpenAI | Anthropic |
|---|---|---|
| Client | `openai.AsyncOpenAI` | `anthropic.AsyncAnthropic` |
| Env var | `OPENAI_API_KEY` | `ANTHROPIC_API_KEY` |
| Model | `"gpt-4o"` | `"claude-sonnet-4-6"` |
| System prompt | in messages list | top-level `system=` param |
| Response text | `response.choices[0].message.content` | `response.content[0].text` |
| Create method | `client.chat.completions.create(...)` | `client.messages.create(...)` |

No other files need changing.

---

## Project structure

```
vibecheck/
├── .env                              # Secrets (not committed)
├── .env.example
├── CLAUDE.md                         # Project instructions for Claude Code
├── VIBECHECK.md                      # Architecture decisions + gotchas
├── backend/
│   ├── main.py                       # FastAPI entrypoint
│   ├── db.py                         # Async SQLAlchemy setup
│   ├── mcp_server.py                 # MCP server (11 tools)
│   ├── pyproject.toml
│   ├── models/session.py             # Session, Quiz, Attempt, Insight, FocusArea, RepoGroup, Repo, RepoConnection
│   ├── schemas/session.py            # All Pydantic schemas
│   ├── routers/
│   │   ├── sessions.py
│   │   ├── quiz.py
│   │   ├── results.py
│   │   ├── insights.py
│   │   ├── analytics.py
│   │   ├── codebase.py               # Scan, quiz, self-brief, focus areas
│   │   └── multi_repo.py             # Repo group CRUD + cross-repo analysis
│   └── services/
│       ├── claude_service.py         # Quiz gen + answer evaluation + self-brief (OpenAI)
│       ├── quiz_engine.py            # Orchestrates DB + AI for quizzes
│       ├── insights_service.py       # Session intelligence extraction
│       ├── analytics_service.py      # Cross-session topic scoring + catch-up
│       ├── codebase_service.py       # Directory scanning + code-first quiz gen
│       ├── self_brief_service.py     # AI codebase onboarding brief generation
│       └── multi_repo_service.py     # Cross-repo connection analysis
├── frontend/
│   ├── src/
│   │   ├── api/sessions.ts           # All typed API wrappers
│   │   └── pages/
│   │       ├── Home.tsx
│   │       ├── NewSession.tsx
│   │       ├── SessionDetail.tsx
│   │       ├── Quiz.tsx
│   │       ├── Results.tsx
│   │       ├── Insights.tsx
│   │       ├── Analytics.tsx
│   │       ├── CodebaseMap.tsx
│   │       ├── SelfBrief.tsx         # AI codebase onboarding brief UI
│   │       ├── SelfBriefComponents.tsx
│   │       ├── MultiRepo.tsx         # Multi-repo group manager UI
│   │       └── MultiRepoComponents.tsx
│   └── package.json
└── hooks/
    └── session_end.py                # Claude Code Stop hook
```

---

## API reference

```
# Sessions
POST   /api/sessions
GET    /api/sessions
GET    /api/sessions/{id}
DELETE /api/sessions/{id}

# Quiz
POST   /api/sessions/{id}/quiz
GET    /api/sessions/{id}/quiz

# Attempts & Results
POST   /api/sessions/{id}/attempt
GET    /api/sessions/{id}/results

# Session Intelligence
POST   /api/sessions/{id}/insights
GET    /api/sessions/{id}/insights
POST   /api/sessions/{id}/insights/apply

# Analytics
GET    /api/analytics
POST   /api/analytics/catchup

# Codebase
POST   /api/codebase/scan
POST   /api/codebase/quiz

# AI Self-Brief
POST   /api/codebase/brief
POST   /api/codebase/brief/apply

# Focus Areas
GET    /api/focus
POST   /api/focus
DELETE /api/focus/{id}

# Multi-Repo
GET    /api/repos/groups
POST   /api/repos/groups
GET    /api/repos/groups/{id}
POST   /api/repos/groups/{id}/analyze
GET    /api/repos/groups/{id}/context
```
