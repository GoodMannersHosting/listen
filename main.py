"""Main FastAPI application."""
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import aiofiles

from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Query, Form, BackgroundTasks
from typing import Union
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc
import bcrypt

from database import get_db, init_db
from models import Profile, Conversation, Transcript, TranscriptSegment, Speaker, ApiKey, ProcessingJob
from schemas import (
    ProfileCreate, ProfileUpdate, ProfileResponse,
    ConversationResponse, ConversationDetail, ConversationUpdate,
    TranscriptResponse, TranscriptDetail,
    UploadResponse, SummarizeRequest, SummarizeResponse,
    ActionItemsRequest, ActionItemsResponse,
    ApiKeyCreate, ApiKeyResponse, JobStatusResponse
)
from config import settings
from audio_processor import chunk_audio, get_audio_duration
from transcriber import get_transcriber
from diarization_service import get_diarization_service
from llm_service import get_llm_service


# Initialize FastAPI app
app = FastAPI(title="Audio Transcription Tool", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure upload directory exists
os.makedirs(settings.upload_dir, exist_ok=True)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()


# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# Background processing function
async def process_audio_background(
    conversation_id: int,
    audio_file_path: str,
    file_name: str,
    profile_id: int,
    diarization: bool,
    generate_summary: bool,
    generate_action_items: bool,
    job_id: int
):
    """Background task to process audio file."""
    from database import SessionLocal
    db = SessionLocal()
    try:
        # Update job status to processing
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if job:
            job.status = "processing"
            job.progress = 5  # Started processing
            db.commit()
        
        # Get audio duration (5-10%)
        duration = get_audio_duration(audio_file_path)
        if job:
            job.progress = 10
            db.commit()
        
        # Chunk audio if needed (10-15%)
        chunks = chunk_audio(audio_file_path, chunk_duration=settings.audio_chunk_duration)
        num_chunks = len(chunks)
        if job:
            job.progress = 15
            db.commit()
        
        # Transcribe with progress tracking
        transcriber = get_transcriber()
        if num_chunks > 1:
            # Track progress per chunk (15-80% for transcription)
            transcript_result = transcriber.transcribe_chunks(chunks)
            # Note: If transcriber.transcribe_chunks doesn't support progress callbacks,
            # we'll update progress after completion
            if job:
                job.progress = 80
                db.commit()
        else:
            # Single chunk transcription (15-80%)
            transcript_result = transcriber.transcribe(chunks[0][0])
            if job:
                job.progress = 80
                db.commit()
        
        # Get conversation
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Create transcript record
        transcript = Transcript(
            conversation_id=conversation.id,
            file_name=file_name,
            transcript_text=transcript_result.text,
            duration=duration,
            language=transcript_result.language,
            transcription_model=settings.transcription_model,
            audio_file_url=f"/api/audio/{conversation.id}"
        )
        db.add(transcript)
        db.commit()
        db.refresh(transcript)
        
        # Update job with transcript ID
        if job:
            job.transcript_id = transcript.id
            db.commit()
        
        # Save transcript segments
        for seg in transcript_result.segments:
            db_segment = TranscriptSegment(
                transcript_id=transcript.id,
                start_time=seg.start,
                end_time=seg.end,
                text=seg.text,
                confidence=seg.confidence
            )
            db.add(db_segment)
        
        # Speaker diarization if enabled
        if diarization and settings.enable_diarization:
            diarization_service = get_diarization_service()
            if diarization_service.is_enabled():
                diarization_segments = diarization_service.diarize(audio_file_path)
                # Align speakers with transcript segments
                trans_segments = [
                    {"start_time": seg.start, "end_time": seg.end, "text": seg.text}
                    for seg in transcript_result.segments
                ]
                aligned = diarization_service.align_speakers_to_transcript(trans_segments, diarization_segments)
                
                # Update segments with speaker labels
                for i, seg_data in enumerate(aligned):
                    if i < len(transcript_result.segments) and "speaker_label" in seg_data:
                        db.query(TranscriptSegment).filter(
                            TranscriptSegment.transcript_id == transcript.id,
                            TranscriptSegment.start_time == transcript_result.segments[i].start
                        ).update({"speaker_label": seg_data["speaker_label"]})
        
        db.commit()
        
        # Update progress after saving segments (80-85%)
        if job:
            job.progress = 85
            db.commit()
        
        # Generate summary if requested (85-95%)
        if generate_summary:
            llm_service = get_llm_service()
            try:
                if job:
                    job.progress = 87
                    db.commit()
                summary = await llm_service.generate_summary(
                    transcript_result.text,
                    db,
                    profile_id=profile_id
                )
                transcript.summary = summary
                db.commit()
                if job:
                    job.progress = 92
                    db.commit()
            except Exception as e:
                print(f"Warning: Summary generation failed: {e}")
        
        # Generate action items if requested (92-97%)
        if generate_action_items:
            llm_service = get_llm_service()
            try:
                if job:
                    job.progress = 94
                    db.commit()
                action_items = await llm_service.extract_action_items(
                    transcript_result.text,
                    db,
                    profile_id=profile_id
                )
                transcript.action_items = action_items
                db.commit()
                if job:
                    job.progress = 97
                    db.commit()
            except Exception as e:
                print(f"Warning: Action items extraction failed: {e}")
        
        # Update job status to completed
        if job:
            job.status = "completed"
            job.progress = 100
            job.result = "success"
            db.commit()
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in background processing: {str(e)}")
        print(f"Traceback: {error_trace}")
        
        # Update job status to failed
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.result = str(e)
            db.commit()
        
        # Clean up conversation on error
        try:
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation:
                db.delete(conversation)
                db.commit()
        except:
            db.rollback()
    finally:
        db.close()


# Profile Management Endpoints
@app.post("/api/profiles", response_model=ProfileResponse, status_code=201)
async def create_profile(profile: ProfileCreate, db: Session = Depends(get_db)):
    """Create a new profile."""
    # Check if profile with same name exists
    existing = db.query(Profile).filter(Profile.name == profile.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Profile with this name already exists")
    
    db_profile = Profile(**profile.dict())
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile


@app.get("/api/profiles", response_model=List[ProfileResponse])
async def list_profiles(db: Session = Depends(get_db)):
    """List all profiles."""
    return db.query(Profile).filter(Profile.is_active == True).all()


@app.get("/api/profiles/{profile_id}", response_model=ProfileResponse)
async def get_profile(profile_id: int, db: Session = Depends(get_db)):
    """Get profile details."""
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@app.put("/api/profiles/{profile_id}", response_model=ProfileResponse)
async def update_profile(profile_id: int, profile_update: ProfileUpdate, db: Session = Depends(get_db)):
    """Update profile."""
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    update_data = profile_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)
    
    profile.last_accessed_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return profile


@app.delete("/api/profiles/{profile_id}", status_code=204)
async def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    """Delete profile and all associated data."""
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Delete associated files
    profile_dir = os.path.join(settings.upload_dir, str(profile_id))
    if os.path.exists(profile_dir):
        shutil.rmtree(profile_dir)
    
    db.delete(profile)
    db.commit()
    return None


# Conversation Management Endpoints
@app.get("/api/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    profile_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """List conversations for a profile."""
    query = db.query(Conversation)
    if profile_id:
        query = query.filter(Conversation.profile_id == profile_id)
    
    return query.order_by(desc(Conversation.created_at)).all()


@app.get("/api/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """Get conversation details."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    transcript = db.query(Transcript).filter(Transcript.conversation_id == conversation_id).first()
    
    result = ConversationDetail(**conversation.__dict__)
    if transcript:
        # Convert transcript to response schema
        transcript_dict = {
            "id": transcript.id,
            "conversation_id": transcript.conversation_id,
            "file_name": transcript.file_name,
            "transcript_text": transcript.transcript_text,
            "duration": transcript.duration,
            "language": transcript.language,
            "transcription_model": transcript.transcription_model,
            "summary": transcript.summary,
            "action_items": transcript.action_items,
            "audio_file_url": transcript.audio_file_url,
            "created_at": transcript.created_at,
            "updated_at": transcript.updated_at
        }
        result.transcript = TranscriptResponse(**transcript_dict)
    
    return result


@app.put("/api/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    conversation_update: ConversationUpdate,
    db: Session = Depends(get_db)
):
    """Update conversation title."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    update_data = conversation_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(conversation, key, value)
    
    conversation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(conversation)
    return conversation


@app.delete("/api/conversations/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """Delete conversation and associated files."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Delete associated files
    if os.path.exists(conversation.audio_file_path):
        os.remove(conversation.audio_file_path)
    
    conversation_dir = os.path.dirname(conversation.audio_file_path)
    if os.path.exists(conversation_dir) and not os.listdir(conversation_dir):
        os.rmdir(conversation_dir)
    
    db.delete(conversation)
    db.commit()
    return None


# File Upload and Processing
@app.post("/api/upload", response_model=UploadResponse)
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    profile_id: Optional[int] = Form(None),
    diarization: Union[bool, str, None] = Form(False),
    generate_summary: Union[bool, str, None] = Form(False),
    generate_action_items: Union[bool, str, None] = Form(False),
    db: Session = Depends(get_db)
):
    """Upload and process audio file."""
    # Normalize boolean form values (handle string "true"/"false" from FormData)
    def normalize_bool(value):
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)
    
    diarization = normalize_bool(diarization)
    generate_summary = normalize_bool(generate_summary)
    generate_action_items = normalize_bool(generate_action_items)
    
    # Validate file type
    allowed_extensions = {".mp3", ".m4a", ".mp4", ".ogg", ".wav", ".flac"}
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}")
    
    # Get or create profile
    if profile_id:
        profile = db.query(Profile).filter(Profile.id == profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
    else:
        # Get first active profile or create default
        profile = db.query(Profile).filter(Profile.is_active == True).first()
        if not profile:
            profile = Profile(name="default", display_name="Default Profile")
            db.add(profile)
            db.commit()
            db.refresh(profile)
    
    # Create conversation
    conversation = Conversation(
        profile_id=profile.id,
        title=file.filename,
        audio_file_path=""  # Will be set after saving
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    # Save uploaded file (async, chunked for large files)
    profile_dir = os.path.join(settings.upload_dir, str(profile.id))
    conversation_dir = os.path.join(profile_dir, str(conversation.id))
    os.makedirs(conversation_dir, exist_ok=True)
    
    audio_file_path = os.path.join(conversation_dir, f"audio{file_ext}")
    async with aiofiles.open(audio_file_path, "wb") as f:
        # Read and write in chunks to avoid loading entire file into memory
        while chunk := await file.read(8192):  # 8KB chunks
            await f.write(chunk)
    
    conversation.audio_file_path = audio_file_path
    db.commit()
    
    # Create processing job
    job = ProcessingJob(
        conversation_id=conversation.id,
        transcript_id=None,  # Will be updated when transcript is created
        job_type="transcription",
        status="pending"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Start background processing
    background_tasks.add_task(
        process_audio_background,
        conversation.id,
        audio_file_path,
        file.filename,
        profile.id,
        diarization,
        generate_summary,
        generate_action_items,
        job.id
    )
    
    # Return immediately with job ID
    return UploadResponse(
        conversation_id=conversation.id,
        transcript_id=None,
        transcript=None,
        summary=None,
        action_items=None,
        status="processing",
        message=f"Audio upload successful. Processing started. Job ID: {job.id}"
    )


# Job Status Endpoint
@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: int, db: Session = Depends(get_db)):
    """Get processing job status."""
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress or 0,
        conversation_id=job.conversation_id,
        transcript_id=job.transcript_id,
        message=f"Job status: {job.status}",
        error=job.result if job.status == "failed" else None
    )


@app.get("/api/conversations/{conversation_id}/job", response_model=JobStatusResponse)
async def get_conversation_job(conversation_id: int, db: Session = Depends(get_db)):
    """Get processing job for a conversation."""
    job = db.query(ProcessingJob).filter(
        ProcessingJob.conversation_id == conversation_id
    ).order_by(ProcessingJob.created_at.desc()).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="No job found for this conversation")
    
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress or 0,
        conversation_id=job.conversation_id,
        transcript_id=job.transcript_id,
        message=f"Job status: {job.status}",
        error=job.result if job.status == "failed" else None
    )


# Audio File Serving
@app.get("/api/audio/{conversation_id}")
async def get_audio(conversation_id: int, db: Session = Depends(get_db)):
    """Serve audio file for playback."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation or not os.path.exists(conversation.audio_file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        conversation.audio_file_path,
        media_type="audio/mpeg",
        filename=os.path.basename(conversation.audio_file_path)
    )


# Transcript Endpoints
@app.get("/api/conversations/{conversation_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(conversation_id: int, db: Session = Depends(get_db)):
    """Get transcript for a conversation."""
    transcript = db.query(Transcript).filter(Transcript.conversation_id == conversation_id).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript


@app.get("/api/conversations/{conversation_id}/transcript/segments", response_model=List)
async def get_transcript_segments(conversation_id: int, db: Session = Depends(get_db)):
    """Get transcript segments with timestamps."""
    transcript = db.query(Transcript).filter(Transcript.conversation_id == conversation_id).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    
    segments = db.query(TranscriptSegment).filter(
        TranscriptSegment.transcript_id == transcript.id
    ).order_by(TranscriptSegment.start_time).all()
    
    return [
        {
            "id": seg.id,
            "start_time": seg.start_time,
            "end_time": seg.end_time,
            "text": seg.text,
            "speaker_label": seg.speaker_label,
            "confidence": seg.confidence
        }
        for seg in segments
    ]


# LLM Operations
@app.post("/api/conversations/{conversation_id}/summarize", response_model=SummarizeResponse)
async def summarize_conversation(
    conversation_id: int,
    request: SummarizeRequest,
    db: Session = Depends(get_db)
):
    """Generate summary from transcript."""
    transcript = db.query(Transcript).filter(Transcript.conversation_id == conversation_id).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    
    text = request.text or transcript.transcript_text
    
    llm_service = get_llm_service()
    summary = await llm_service.generate_summary(
        text,
        db,
        api_key_id=request.api_key_id,
        profile_id=transcript.conversation.profile_id
    )
    
    transcript.summary = summary
    db.commit()
    
    return SummarizeResponse(summary=summary, transcript_id=transcript.id)


@app.post("/api/conversations/{conversation_id}/action-items", response_model=ActionItemsResponse)
async def extract_action_items(
    conversation_id: int,
    request: ActionItemsRequest,
    db: Session = Depends(get_db)
):
    """Extract action items from transcript."""
    transcript = db.query(Transcript).filter(Transcript.conversation_id == conversation_id).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    
    text = request.text or transcript.transcript_text
    
    llm_service = get_llm_service()
    action_items = await llm_service.extract_action_items(
        text,
        db,
        api_key_id=request.api_key_id,
        profile_id=transcript.conversation.profile_id
    )
    
    transcript.action_items = action_items
    db.commit()
    
    return ActionItemsResponse(action_items=action_items, transcript_id=transcript.id)


# API Key Management
@app.post("/api/api-keys", response_model=ApiKeyResponse, status_code=201)
async def create_api_key(api_key: ApiKeyCreate, db: Session = Depends(get_db)):
    """Create new API key (hashed for storage)."""
    # Hash the API key
    key_hash = bcrypt.hashpw(api_key.key.encode(), bcrypt.gensalt(settings.api_key_hash_rounds)).decode()
    
    db_api_key = ApiKey(
        name=api_key.name,
        key_hash=key_hash,
        profile_id=api_key.profile_id
    )
    db.add(db_api_key)
    db.commit()
    db.refresh(db_api_key)
    
    return ApiKeyResponse(
        id=db_api_key.id,
        name=db_api_key.name,
        profile_id=db_api_key.profile_id,
        created_at=db_api_key.created_at,
        is_active=db_api_key.is_active
    )


@app.get("/api/api-keys", response_model=List[ApiKeyResponse])
async def list_api_keys(
    profile_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """List API keys."""
    query = db.query(ApiKey).filter(ApiKey.is_active == True)
    if profile_id:
        query = query.filter(ApiKey.profile_id == profile_id)
    return query.all()


@app.get("/api/api-keys/{key_id}", response_model=ApiKeyResponse)
async def get_api_key(key_id: int, db: Session = Depends(get_db)):
    """Get API key metadata."""
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    return ApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        profile_id=api_key.profile_id,
        created_at=api_key.created_at,
        is_active=api_key.is_active
    )


@app.delete("/api/api-keys/{key_id}", status_code=204)
async def delete_api_key(key_id: int, db: Session = Depends(get_db)):
    """Delete/deactivate API key."""
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    api_key.is_active = False
    db.commit()
    return None


# Frontend
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve main web interface."""
    with open("templates/index.html", "r") as f:
        return HTMLResponse(content=f.read())
