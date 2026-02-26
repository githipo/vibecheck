from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Session schemas
# ---------------------------------------------------------------------------


class SessionCreate(BaseModel):
    title: str
    transcript: str
    source_type: Literal["claude_code", "chatgpt", "cursor", "generic"]


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source_type: str
    status: str
    created_at: datetime


class SessionDetail(SessionOut):
    transcript: str


# ---------------------------------------------------------------------------
# Quiz / Question schemas
# ---------------------------------------------------------------------------


class QuestionOut(BaseModel):
    id: str | int
    type: str  # multiple_choice | short_answer | code_explanation
    question: str
    choices: list[str] | None = None
    answer_key: str | None = None  # only present for multiple_choice


class QuizOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    questions: list[QuestionOut]
    created_at: datetime


# ---------------------------------------------------------------------------
# Attempt / Answer / Evaluation schemas
# ---------------------------------------------------------------------------


class AnswerIn(BaseModel):
    question_id: str | int
    answer_text: str


class AttemptCreate(BaseModel):
    answers: list[AnswerIn]


class EvaluationOut(BaseModel):
    question_id: str | int
    verdict: Literal["correct", "partial", "incorrect"]
    score: int  # 0–100
    feedback: str


class AttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    quiz_id: int
    score: float
    feedback_summary: str
    evaluations: list[EvaluationOut]
    created_at: datetime


# ---------------------------------------------------------------------------
# Insight schemas
# ---------------------------------------------------------------------------


class DecisionOut(BaseModel):
    decision: str
    rationale: str
    alternatives_rejected: list[str]


class PatternOut(BaseModel):
    pattern: str
    description: str


class GotchaOut(BaseModel):
    issue: str
    context: str


class ProposedRuleOut(BaseModel):
    rule: str
    rationale: str
    section: str  # e.g. "Code Style", "Architecture", "Testing"


class InsightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    decisions: list[DecisionOut]
    patterns: list[PatternOut]
    gotchas: list[GotchaOut]
    proposed_rules: list[ProposedRuleOut]
    created_at: datetime


class ApplyInsightRequest(BaseModel):
    file_path: str  # Absolute path to CLAUDE.md to append to


# ---------------------------------------------------------------------------
# Analytics schemas
# ---------------------------------------------------------------------------


class TopicScore(BaseModel):
    topic: str
    avg_score: float           # 0–100
    question_count: int
    sessions_appeared_in: int
    is_blind_spot: bool        # True if avg_score < 60 and question_count >= 2


class AnalyticsOut(BaseModel):
    total_sessions: int
    completed_sessions: int    # sessions with at least one attempt
    total_questions_answered: int
    overall_avg_score: float
    topic_scores: list[TopicScore]
    blind_spots: list[TopicScore]   # subset of topic_scores where is_blind_spot=True
    trend: list[dict]               # [{"session_id": int, "title": str, "score": float, "date": str}]


class CatchupRequest(BaseModel):
    topic: str


class CatchupOut(BaseModel):
    topic: str
    brief: str   # The AI-generated catch-up explanation (markdown)
    source_sessions: list[int]  # session IDs that contributed context


# ---------------------------------------------------------------------------
# Codebase Intelligence schemas
# ---------------------------------------------------------------------------


class FileRisk(BaseModel):
    path: str                    # absolute file path
    relative_path: str           # relative to scanned root
    language: str                # "python", "typescript", etc.
    line_count: int
    import_count: int
    risk_score: float            # 0–100, AI-assessed
    risk_factors: list[str]      # e.g. ["High nesting", "No comments", "Critical dependency"]
    blast_radius: str            # short sentence: "Imported by 8 modules"
    is_focus: bool               # True if this path matches a FocusArea


class ScanResult(BaseModel):
    root: str
    file_count: int
    files: list[FileRisk]        # sorted by risk_score descending


class ScanRequest(BaseModel):
    directory: str               # absolute path to scan
    extensions: list[str] = [".py", ".ts", ".tsx", ".js", ".go", ".rs", ".java"]
    max_files: int = 50          # cap to avoid enormous scans


class FocusAreaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    value: str
    label: str
    created_at: datetime


class FocusAreaCreate(BaseModel):
    type: str   # "file" or "concept"
    value: str
    label: str


class CodeQuizRequest(BaseModel):
    file_path: str               # absolute path to code file
    title: str | None = None     # optional override; defaults to filename


# ---------------------------------------------------------------------------
# AI Self-Brief schemas
# ---------------------------------------------------------------------------


class KeyEntryPoint(BaseModel):
    file: str
    role: str  # e.g. "FastAPI app entrypoint", "Main DB session factory"


class AIBrief(BaseModel):
    architecture_summary: str
    non_obvious_conventions: list[str]
    critical_invariants: list[str]
    common_mistakes_to_avoid: list[str]
    key_entry_points: list[KeyEntryPoint]


class SuggestedAgent(BaseModel):
    name: str           # e.g. "db-agent"
    role: str           # e.g. "Database & schema specialist"
    description: str
    system_prompt: str  # Full system prompt, ready to use
    claude_md_entry: str  # Ready-to-paste CLAUDE.md block


class SelfBriefOut(BaseModel):
    directory: str
    brief: AIBrief
    suggested_agents: list[SuggestedAgent]
    generated_at: str   # ISO datetime string


class ApplySelfBriefRequest(BaseModel):
    file_path: str
    brief: AIBrief
    suggested_agents: list[SuggestedAgent]
    include_agents: bool = True


# ---------------------------------------------------------------------------
# Multi-Repo Awareness schemas
# ---------------------------------------------------------------------------


class RepoIn(BaseModel):
    name: str
    path: str
    role: str = "other"


class RepoGroupCreate(BaseModel):
    name: str
    description: str = ""
    repos: list[RepoIn]


class RepoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    name: str
    path: str
    role: str
    created_at: datetime


class RepoConnectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_repo_id: int
    to_repo_id: int
    connection_type: str
    description: str
    evidence: str
    created_at: datetime


class RepoGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    created_at: datetime
    repos: list[RepoOut]


class RepoGroupDetail(RepoGroupOut):
    connections: list[RepoConnectionOut]


class RepoContextOut(BaseModel):
    group_name: str
    summary: str          # AI-generated paragraph on how repos connect
    connections: list[RepoConnectionOut]
    repo_briefs: dict[str, str]   # repo name -> one-sentence role description
