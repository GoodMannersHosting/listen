from __future__ import annotations

import json
import os
import re
import traceback
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import Job, Prompt, Transcript, TranscriptSegment, Upload
from app.services.openwebui import OpenWebUIClient
from worker.celery_app import celery_app
from worker.pipeline import chunk_wav, normalize_to_wav, transcribe_chunk


def _update_job(db: Session, job: Job, **kwargs) -> None:
    for k, v in kwargs.items():
        setattr(job, k, v)
    db.commit()


def _get_prompt(db: Session, kind: str, preferred_id: int | None) -> str:
    if preferred_id is not None:
        p = db.query(Prompt).filter(Prompt.id == preferred_id, Prompt.kind == kind).first()
        if p:
            return p.content
    p = db.query(Prompt).filter(Prompt.kind == kind, Prompt.is_default == True).first()
    return p.content if p else ""


def _normalize_markdown(md: str) -> str:
    if not md:
        return md
    # Convert HTML line breaks to actual newlines.
    return re.sub(r"<br\s*/?>", "\n", md, flags=re.IGNORECASE)


@celery_app.task(name="worker.tasks.process_upload")
def process_upload(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return
        upload = db.query(Upload).filter(Upload.id == job.upload_id).first()
        if not upload:
            _update_job(db, job, status="failed", error="upload not found", finished_at=datetime.utcnow(), progress=100)
            return

        job.status = "processing"
        job.started_at = datetime.utcnow()
        job.phase = "chunking"
        job.progress = 5
        db.commit()

        # Prepare paths
        upload_dir = os.path.join(settings.upload_dir, str(upload.id))
        os.makedirs(upload_dir, exist_ok=True)
        norm_wav = os.path.join(upload_dir, "normalized.wav")
        chunk_dir = os.path.join(upload_dir, "chunks")

        normalize_to_wav(upload.stored_path, norm_wav)
        chunks = chunk_wav(norm_wav, chunk_dir, settings.audio_chunk_seconds)
        job.total_chunks = len(chunks)
        job.current_chunk = 0
        job.progress = 10
        job.phase = "transcribing"
        db.commit()

        # Transcribe chunk-by-chunk with progress updates
        # faster-whisper runs per chunk inside transcribe_chunks; we update current_chunk around that
        transcript_text_parts: list[str] = []
        all_segments: list[tuple[float, float, str]] = []
        language: str | None = None

        for idx, chunk_path in enumerate(chunks, start=1):
            job.current_chunk = idx
            # 10..80% while transcribing
            job.progress = 10 + int(70 * idx / max(1, len(chunks)))
            db.commit()

            text, segs, lang = transcribe_chunk(chunk_path)
            if lang and not language:
                language = lang
            if text:
                transcript_text_parts.append(text)
            for s in segs:
                offset = (idx - 1) * settings.audio_chunk_seconds
                all_segments.append((s.start + offset, s.end + offset, s.text))

        transcript_text = " ".join(transcript_text_parts).strip()

        # Persist transcript + segments
        db.query(TranscriptSegment).filter(TranscriptSegment.upload_id == upload.id).delete()
        db.query(Transcript).filter(Transcript.upload_id == upload.id).delete()
        db.commit()

        tr = Transcript(upload_id=upload.id, text=transcript_text)
        db.add(tr)

        for start, end, text in all_segments:
            db.add(TranscriptSegment(upload_id=upload.id, start_time=start, end_time=end, text=text))

        upload.language = language
        db.commit()

        job.progress = 85
        job.phase = "summarizing" if job.summarize else ("action_items" if job.generate_action_items else None)
        db.commit()

        # Optional LLM work
        if job.summarize or job.generate_action_items:
            client = OpenWebUIClient(
                settings.openwebui_url,
                settings.openwebui_api_key,
                temperature=settings.openwebui_temperature,
                max_tokens=settings.openwebui_max_tokens,
            )
            model = job.llm_model or settings.openwebui_default_model

            if job.summarize:
                prompt = _get_prompt(db, "summary", job.prompt_summary_id)
                summary = _run_async(client.chat_completion(model=model, system_prompt=prompt, user_text=transcript_text))
                upload.summary = _normalize_markdown(summary)
                db.commit()

            if job.generate_action_items:
                prompt = _get_prompt(db, "action_items", job.prompt_action_items_id)
                raw = _run_async(client.chat_completion(model=model, system_prompt=prompt, user_text=transcript_text))
                upload.action_items = _best_effort_json(raw)
                db.commit()

        job.status = "completed"
        job.progress = 100
        job.phase = None
        job.finished_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "failed"
                job.progress = 100
                job.error = str(e)
                job.finished_at = datetime.utcnow()
                db.commit()
        finally:
            traceback.print_exc()
    finally:
        db.close()


@celery_app.task(name="worker.tasks.process_llm")
def process_llm(job_id: int) -> None:
    """
    Re-run LLM-only steps (summary/action_items) using the existing transcript.
    Does not re-run ffmpeg / faster-whisper.
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return
        upload = db.query(Upload).filter(Upload.id == job.upload_id).first()
        if not upload:
            _update_job(db, job, status="failed", error="upload not found", finished_at=datetime.utcnow(), progress=100)
            return

        tr = db.query(Transcript).filter(Transcript.upload_id == upload.id).first()
        transcript_text = (tr.text if tr else "") or ""
        if not transcript_text.strip():
            _update_job(
                db,
                job,
                status="failed",
                error="no transcript available (transcribe first)",
                finished_at=datetime.utcnow(),
                progress=100,
            )
            return

        job.status = "processing"
        job.started_at = datetime.utcnow()
        job.progress = 10
        job.phase = "summarizing" if job.summarize else ("action_items" if job.generate_action_items else None)
        db.commit()

        client = OpenWebUIClient(
            settings.openwebui_url,
            settings.openwebui_api_key,
            temperature=settings.openwebui_temperature,
            max_tokens=settings.openwebui_max_tokens,
        )
        model = job.llm_model or settings.openwebui_default_model

        if job.summarize:
            job.phase = "summarizing"
            job.progress = 25 if job.generate_action_items else 50
            db.commit()
            prompt = _get_prompt(db, "summary", job.prompt_summary_id)
            summary = _run_async(client.chat_completion(model=model, system_prompt=prompt, user_text=transcript_text))
            upload.summary = _normalize_markdown(summary)
            db.commit()

        if job.generate_action_items:
            job.phase = "action_items"
            job.progress = 75
            db.commit()
            prompt = _get_prompt(db, "action_items", job.prompt_action_items_id)
            raw = _run_async(client.chat_completion(model=model, system_prompt=prompt, user_text=transcript_text))
            upload.action_items = _best_effort_json(raw)
            db.commit()

        job.status = "completed"
        job.progress = 100
        job.phase = None
        job.finished_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "failed"
                job.progress = 100
                job.error = str(e)
                job.finished_at = datetime.utcnow()
                db.commit()
        finally:
            traceback.print_exc()
    finally:
        db.close()


def _best_effort_json(raw: str):
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        return json.loads(raw)
    except Exception:
        return {"raw": raw}


def _run_async(coro):
    # Celery task is sync; run async HTTP client calls.
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        return asyncio.run_coroutine_threadsafe(coro, loop).result()
    return asyncio.run(coro)

