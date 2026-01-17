"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# Profile Schemas
class ProfileBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, max_length=100)


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, max_length=100)


class ProfileResponse(ProfileBase):
    id: int
    created_at: datetime
    last_accessed_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


# Conversation Schemas
class ConversationBase(BaseModel):
    title: Optional[str] = None


class ConversationCreate(ConversationBase):
    profile_id: Optional[int] = None


class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)


class ConversationResponse(ConversationBase):
    id: int
    profile_id: int
    audio_file_path: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ConversationDetail(ConversationResponse):
    transcript: Optional["TranscriptResponse"] = None


# Transcript Schemas
class TranscriptSegmentResponse(BaseModel):
    id: int
    start_time: float
    end_time: float
    text: str
    speaker_label: Optional[str] = None
    confidence: Optional[float] = None
    
    class Config:
        from_attributes = True


class TranscriptBase(BaseModel):
    file_name: str
    transcript_text: str
    duration: Optional[float] = None
    language: Optional[str] = None
    transcription_model: Optional[str] = None


class TranscriptResponse(TranscriptBase):
    id: int
    conversation_id: int
    summary: Optional[str] = None
    action_items: Optional[List[Dict[str, Any]]] = None
    audio_file_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TranscriptDetail(TranscriptResponse):
    segments: List[TranscriptSegmentResponse] = []


# API Key Schemas
class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    key: str = Field(..., min_length=1)
    profile_id: Optional[int] = None


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    profile_id: Optional[int] = None
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


# Upload Schemas
class UploadResponse(BaseModel):
    conversation_id: int
    transcript_id: Optional[int] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    action_items: Optional[List[Dict[str, Any]]] = None
    status: str
    message: str


# Summarization/Action Items Schemas
class SummarizeRequest(BaseModel):
    transcript_id: Optional[int] = None
    text: Optional[str] = None
    api_key_id: Optional[int] = None


class SummarizeResponse(BaseModel):
    summary: str
    transcript_id: int


class ActionItemsRequest(BaseModel):
    transcript_id: Optional[int] = None
    text: Optional[str] = None
    api_key_id: Optional[int] = None


class ActionItemsResponse(BaseModel):
    action_items: List[Dict[str, Any]]
    transcript_id: int


# Job Status Schemas
class JobStatusResponse(BaseModel):
    job_id: int
    status: str  # pending, processing, completed, failed
    progress: int = 0  # Progress percentage (0-100)
    conversation_id: Optional[int] = None
    transcript_id: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None


# Update forward references
ConversationDetail.model_rebuild()
TranscriptDetail.model_rebuild()
