from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class UploadListItem(BaseModel):
    id: int
    display_name: str
    original_filename: str
    created_at: datetime
    duration_seconds: Optional[float] = None
    language: Optional[str] = None


class UploadCreateResponse(BaseModel):
    upload_id: int
    job_id: int


class UploadReprocessRequest(BaseModel):
    summarize: bool = False
    action_items: bool = False
    llm_model: Optional[str] = None


class UploadReprocessResponse(BaseModel):
    upload_id: int
    job_id: int


class UploadDetail(BaseModel):
    id: int
    display_name: str
    original_filename: str
    created_at: datetime
    duration_seconds: Optional[float] = None
    language: Optional[str] = None
    summary: Optional[str] = None
    action_items: Optional[Any] = None

    transcript_text: Optional[str] = None


class UploadRenameRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=200)


class JobStatus(BaseModel):
    id: int
    upload_id: int
    status: str
    phase: Optional[str] = None
    progress: int = 0
    total_chunks: Optional[int] = None
    current_chunk: Optional[int] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class JobStats(BaseModel):
    queued: int
    processing: int
    active: int


class TranscriptSegmentOut(BaseModel):
    id: int
    start_time: float
    end_time: float
    text: str


class PromptOut(BaseModel):
    id: int
    name: str
    kind: str
    content: str
    is_default: bool
    updated_at: datetime


class PromptUpdateRequest(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    is_default: Optional[bool] = None

