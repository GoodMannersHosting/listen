"""SQLAlchemy ORM models."""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Profile(Base):
    """User profile model."""
    __tablename__ = "profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="profile", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="profile", cascade="all, delete-orphan")


class Conversation(Base):
    """Conversation/session model."""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False, index=True)
    title = Column(String, nullable=True)
    audio_file_path = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    profile = relationship("Profile", back_populates="conversations")
    transcript = relationship("Transcript", back_populates="conversation", uselist=False, cascade="all, delete-orphan")


class ApiKey(Base):
    """API key model for Ollama/OpenWebUI."""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    key_hash = Column(String, nullable=False)  # Hashed API key
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    profile = relationship("Profile", back_populates="api_keys")


class Transcript(Base):
    """Transcript model."""
    __tablename__ = "transcripts"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), unique=True, nullable=False, index=True)
    file_name = Column(String, nullable=False)
    transcript_text = Column(Text, nullable=False)
    duration = Column(Float, nullable=True)  # Duration in seconds
    language = Column(String, nullable=True)
    transcription_model = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    action_items = Column(JSON, nullable=True)  # Store as JSON array
    audio_file_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="transcript")
    segments = relationship("TranscriptSegment", back_populates="transcript", cascade="all, delete-orphan")
    speakers = relationship("Speaker", back_populates="transcript", cascade="all, delete-orphan")


class TranscriptSegment(Base):
    """Transcript segment model with timestamps and speaker labels."""
    __tablename__ = "transcript_segments"
    
    id = Column(Integer, primary_key=True, index=True)
    transcript_id = Column(Integer, ForeignKey("transcripts.id"), nullable=False, index=True)
    start_time = Column(Float, nullable=False)  # Start time in seconds
    end_time = Column(Float, nullable=False)  # End time in seconds
    text = Column(Text, nullable=False)
    speaker_label = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    
    # Relationships
    transcript = relationship("Transcript", back_populates="segments")


class Speaker(Base):
    """Speaker information model."""
    __tablename__ = "speakers"
    
    id = Column(Integer, primary_key=True, index=True)
    transcript_id = Column(Integer, ForeignKey("transcripts.id"), nullable=False, index=True)
    speaker_label = Column(String, nullable=False)
    segment_count = Column(Integer, default=0)
    speaker_metadata = Column(JSON, nullable=True)  # Additional speaker metadata
    
    # Relationships
    transcript = relationship("Transcript", back_populates="speakers")


class ProcessingJob(Base):
    """Processing job tracking model."""
    __tablename__ = "processing_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True, index=True)
    transcript_id = Column(Integer, ForeignKey("transcripts.id"), nullable=True, index=True)
    job_type = Column(String, nullable=False)  # e.g., "transcription", "summarization", "action_items", "diarization"
    status = Column(String, default="pending")  # pending, processing, completed, failed
    progress = Column(Integer, default=0)  # Progress percentage (0-100)
    total_chunks = Column(Integer, nullable=True)  # Total number of audio chunks to process
    current_chunk = Column(Integer, nullable=True)  # Current chunk being processed
    result = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
