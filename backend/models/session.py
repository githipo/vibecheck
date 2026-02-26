from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # claude_code | chatgpt | cursor | generic
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending_quiz"
    )  # pending_quiz | quiz_active | completed
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    quizzes: Mapped[list["Quiz"]] = relationship(
        "Quiz", back_populates="session", cascade="all, delete-orphan"
    )
    attempts: Mapped[list["Attempt"]] = relationship(
        "Attempt", back_populates="session", cascade="all, delete-orphan"
    )
    insight: Mapped[Optional["Insight"]] = relationship(
        "Insight", back_populates="session", uselist=False, cascade="all, delete-orphan"
    )


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    questions: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    session: Mapped["Session"] = relationship("Session", back_populates="quizzes")
    attempts: Mapped[list["Attempt"]] = relationship(
        "Attempt", back_populates="quiz", cascade="all, delete-orphan"
    )


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    quiz_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False
    )
    answers: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    evaluations: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    feedback_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    session: Mapped["Session"] = relationship("Session", back_populates="attempts")
    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="attempts")


class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    decisions: Mapped[list] = mapped_column(JSON, nullable=False)
    patterns: Mapped[list] = mapped_column(JSON, nullable=False)
    gotchas: Mapped[list] = mapped_column(JSON, nullable=False)
    proposed_rules: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    session: Mapped["Session"] = relationship("Session", back_populates="insight")


class FocusArea(Base):
    __tablename__ = "focus_areas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String, nullable=False)   # "file" or "concept"
    value: Mapped[str] = mapped_column(String, nullable=False)  # abs file path or concept name
    label: Mapped[str] = mapped_column(String, nullable=False)  # display name
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


# ---------------------------------------------------------------------------
# Multi-Repo Awareness models
# ---------------------------------------------------------------------------


class RepoGroup(Base):
    __tablename__ = "repo_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    repos: Mapped[list["Repo"]] = relationship(
        "Repo", back_populates="group", cascade="all, delete-orphan"
    )
    connections: Mapped[list["RepoConnection"]] = relationship(
        "RepoConnection",
        foreign_keys="RepoConnection.group_id",
        cascade="all, delete-orphan",
    )


class Repo(Base):
    __tablename__ = "repos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repo_groups.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    path: Mapped[str] = mapped_column(String(1000), nullable=False)
    role: Mapped[str] = mapped_column(String(200), nullable=False, default="other")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    group: Mapped["RepoGroup"] = relationship("RepoGroup", back_populates="repos")


class RepoConnection(Base):
    __tablename__ = "repo_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repo_groups.id", ondelete="CASCADE"), nullable=False
    )
    from_repo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repos.id", ondelete="CASCADE"), nullable=False
    )
    to_repo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repos.id", ondelete="CASCADE"), nullable=False
    )
    connection_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    evidence: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
