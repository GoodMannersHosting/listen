from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    stored_path: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Optional LLM results
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_items: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    jobs: Mapped[list["Job"]] = relationship(back_populates="upload", cascade="all, delete-orphan")
    transcript: Mapped[Optional["Transcript"]] = relationship(back_populates="upload", cascade="all, delete-orphan", uselist=False)
    segments: Mapped[list["TranscriptSegment"]] = relationship(back_populates="upload", cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), index=True)

    status: Mapped[str] = mapped_column(String, default="queued", nullable=False)  # queued|processing|completed|failed
    phase: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # uploading|chunking|transcribing|summarizing|action_items
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    total_chunks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_chunk: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    summarize: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    generate_action_items: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    llm_model: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    prompt_summary_id: Mapped[Optional[int]] = mapped_column(ForeignKey("prompts.id", ondelete="SET NULL"), nullable=True)
    prompt_action_items_id: Mapped[Optional[int]] = mapped_column(ForeignKey("prompts.id", ondelete="SET NULL"), nullable=True)

    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    upload: Mapped["Upload"] = relationship(back_populates="jobs")


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), unique=True, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    upload: Mapped["Upload"] = relationship(back_populates="transcript")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), index=True)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    upload: Mapped["Upload"] = relationship(back_populates="segments")


class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)  # summary|action_items
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

