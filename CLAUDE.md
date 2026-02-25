# VibeCheck — CLAUDE.md

## Project Identity

**VibeCheck** is a learning-verification companion for AI-assisted workflows (vibecoding, AI-assisted design, AI-assisted writing, etc.). The core problem it solves: when you let AI do the heavy lifting, you often don't actually understand what was built. VibeCheck watches or ingests your AI session, then quizzes you to prove you do.

---

## Autonomous Operation

Claude makes all implementation decisions in this project unless the user specifies otherwise. No confirmation needed for:
- Library/framework choices within the established stack
- File structure and naming conventions
- UI layout and component design
- Database schema decisions
- API design and endpoint structure
- Refactoring and code organization

Always ask the user before:
- Changing the core stack (Python backend, TSX frontend)
- Integrating paid third-party services beyond the Anthropic API
- Deleting files that contain user-created content or configuration

---

## Subagent Usage

For complex or parallelizable work, Claude should delegate to subagents via the Task tool. Use subagents for:

- **Codebase exploration** — Use the `Explore` subagent to search for files, patterns, or understand how a subsystem works before making changes
- **Implementation planning** — Use the `Plan` subagent when a feature touches 3+ files or requires architectural decisions
- **Parallel implementation** — When building a feature that has independent backend and frontend components, run both as parallel subagents simultaneously
- **Research tasks** — Delegate web searches or documentation lookups to a `general-purpose` subagent to keep the main context clean

Specifically, always use subagents for:
- Any new feature that spans both `backend/` and `frontend/` (run both in parallel)
- Deep codebase searches when you are not confident you know exactly where to look
- Generating quiz questions or evaluating answers via the Claude API (these are service-layer calls, not subagents — but their prompt design should be isolated in `services/`)

---

## Feature Testing Requirements

After implementing any new feature or non-trivial change, Claude must verify it works before considering the task done:

1. **Backend features** — Start the backend server and make real HTTP requests to the new endpoint(s) using `curl` or `httpx`. Confirm expected status codes and response shapes.
2. **Frontend features** — If the frontend is running, confirm the relevant page/component renders without console errors. If not running, at minimum verify `npm run build` passes with no TypeScript errors.
3. **AI-integrated features** (quiz generation, answer evaluation) — Run an end-to-end smoke test: create a real session, trigger the Claude call, and assert the output matches the expected JSON schema.
4. **Database changes** — After any schema change, verify migrations apply cleanly and at least one read + write round-trip succeeds.

If a test fails, fix it before moving on — do not leave the codebase in a broken state.

---

## Stack (non-negotiable)

| Layer     | Technology                                      |
|-----------|-------------------------------------------------|
| Backend   | Python 3.12+, FastAPI, Uvicorn                  |
| Frontend  | React 18+, TypeScript, Vite, TailwindCSS        |
| Database  | SQLite via SQLAlchemy (async with aiosqlite)    |
| AI        | Anthropic Python SDK, model: claude-sonnet-4-6  |
| Packaging | uv (Python), npm (frontend)                     |

---

## Project Structure

```
vibecoding/
├── CLAUDE.md
├── backend/
│   ├── main.py              # FastAPI app entrypoint
│   ├── routers/             # Route modules (sessions, quiz, results)
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # Business logic (claude_service, quiz_engine)
│   ├── db.py                # DB init and session dependency
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Route-level page components
│   │   ├── api/             # API client (fetch wrappers)
│   │   └── main.tsx
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
└── .env.example
```

---

## Core Concepts

### Session
A **Session** is a record of an AI-assisted work event. It has:
- A raw transcript (pasted text or uploaded file)
- A source type (`claude_code`, `chatgpt`, `cursor`, `generic`)
- Metadata: title, created_at, status (`pending_quiz`, `quiz_active`, `completed`)

### Quiz
A **Quiz** is generated from a Session by Claude. It contains:
- 3–7 questions, mix of types: multiple choice, short answer, code-explanation
- A difficulty curve (conceptual → implementation-level)
- Each question targets a specific decision or concept found in the transcript

### Attempt
An **Attempt** records the user's answers to a Quiz. It has:
- Per-answer evaluation by Claude (correct / partial / incorrect + explanation)
- An overall comprehension score (0–100)
- A feedback summary: what the user understands and what to revisit

---

## AI Behavior (Claude API Usage)

### Question Generation Prompt Strategy
- Extract key decisions, patterns, and concepts from the transcript
- Generate questions that cannot be googled trivially — they should require understanding *this specific session*
- Vary question types: "Why did X happen?", "What would break if Y?", "Explain what this code does"
- Never generate questions about boilerplate or trivial details

### Answer Evaluation Strategy
- Be strict but fair — partial credit is real
- Provide specific, educational feedback, not just correct/incorrect
- Reference the original transcript when explaining why an answer is right/wrong
- Output structured JSON: `{ score: 0-100, verdict: "correct|partial|incorrect", feedback: "..." }`

---

## API Design

```
POST   /api/sessions              # Create a session (paste transcript)
GET    /api/sessions              # List all sessions
GET    /api/sessions/{id}         # Get session detail
DELETE /api/sessions/{id}         # Delete session

POST   /api/sessions/{id}/quiz    # Generate quiz from session (calls Claude)
GET    /api/sessions/{id}/quiz    # Get existing quiz

POST   /api/sessions/{id}/attempt # Submit quiz answers (Claude evaluates)
GET    /api/sessions/{id}/results # Get latest attempt results
```

---

## Frontend Pages

1. **Home** (`/`) — Recent sessions list + "New Session" CTA
2. **New Session** (`/sessions/new`) — Paste or upload transcript, select source type
3. **Session Detail** (`/sessions/:id`) — View transcript, quiz status, start quiz button
4. **Quiz** (`/sessions/:id/quiz`) — Step-through question interface, one question at a time
5. **Results** (`/sessions/:id/results`) — Score breakdown, per-answer feedback, retry option

---

## Code Style

### Python
- Type hints everywhere, no bare `dict` return types
- Pydantic models for all request/response shapes
- Async all the way down (async def routes, async SQLAlchemy)
- Services are plain async functions, not classes
- No print statements — use Python `logging`

### TypeScript/React
- Functional components only, no class components
- `const` arrow functions for components
- TailwindCSS utility classes only — no custom CSS files
- API calls live in `src/api/` — never fetch directly from components
- No `any` types — write proper interfaces

### General
- No TODO comments in committed code — either do it or create a task
- Keep files under 300 lines — split when approaching limit
- Prefer explicit over clever

---

## Environment Variables

```
ANTHROPIC_API_KEY=your_key_here
DATABASE_URL=sqlite+aiosqlite:///./vibecheck.db
CORS_ORIGINS=http://localhost:5173
```

---

## Running the Project

```bash
# Backend
cd backend && uv run uvicorn main:app --reload

# Frontend
cd frontend && npm run dev
```

---

## What This Is NOT

- Not a plagiarism detector
- Not a code quality tool
- Not an AI tutor that teaches — it only verifies understanding
- Not a replacement for actually reading what the AI wrote 

