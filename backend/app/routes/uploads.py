from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Job, Prompt, Transcript, TranscriptSegment, Upload
from app.schemas import (
    TranscriptSegmentOut,
    UploadCreateResponse,
    UploadDetail,
    UploadListItem,
    UploadReprocessRequest,
    UploadReprocessResponse,
    UploadRenameRequest,
)
from app.services.storage import ensure_dir, safe_filename, delete_tree
from worker.celery_app import celery_app

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.get("", response_model=list[UploadListItem])
def list_uploads(db: Session = Depends(get_db)) -> list[UploadListItem]:
    rows = db.query(Upload).order_by(Upload.created_at.desc()).all()
    return [
        UploadListItem(
            id=u.id,
            display_name=u.display_name,
            original_filename=u.original_filename,
            created_at=u.created_at,
            duration_seconds=u.duration_seconds,
            language=u.language,
        )
        for u in rows
    ]


@router.get("/{upload_id}", response_model=UploadDetail)
def get_upload(upload_id: int, db: Session = Depends(get_db)) -> UploadDetail:
    u = db.query(Upload).filter(Upload.id == upload_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Upload not found")

    tr = db.query(Transcript).filter(Transcript.upload_id == upload_id).first()
    return UploadDetail(
        id=u.id,
        display_name=u.display_name,
        original_filename=u.original_filename,
        created_at=u.created_at,
        duration_seconds=u.duration_seconds,
        language=u.language,
        summary=u.summary,
        action_items=u.action_items,
        transcript_text=tr.text if tr else None,
    )


@router.get("/{upload_id}/segments", response_model=list[TranscriptSegmentOut])
def get_segments(upload_id: int, db: Session = Depends(get_db)) -> list[TranscriptSegmentOut]:
    rows = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.upload_id == upload_id)
        .order_by(TranscriptSegment.start_time.asc())
        .all()
    )
    return [TranscriptSegmentOut(id=s.id, start_time=s.start_time, end_time=s.end_time, text=s.text) for s in rows]


@router.get("/{upload_id}/audio")
def get_audio(upload_id: int, db: Session = Depends(get_db)):
    u = db.query(Upload).filter(Upload.id == upload_id).first()
    if not u or not u.stored_path or not os.path.exists(u.stored_path):
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(u.stored_path, filename=u.original_filename)


@router.patch("/{upload_id}")
def rename_upload(upload_id: int, req: UploadRenameRequest, db: Session = Depends(get_db)) -> dict:
    u = db.query(Upload).filter(Upload.id == upload_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Upload not found")
    u.display_name = req.display_name.strip()
    u.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.delete("/{upload_id}")
def delete_upload(upload_id: int, db: Session = Depends(get_db)) -> dict:
    u = db.query(Upload).filter(Upload.id == upload_id).first()
    if not u:
        return {"ok": True}

    # best-effort file cleanup: delete upload directory
    upload_dir = os.path.join(settings.upload_dir, str(u.id))
    db.delete(u)
    db.commit()
    delete_tree(upload_dir)
    return {"ok": True}


@router.post("", response_model=UploadCreateResponse)
def create_upload(
    file: UploadFile = File(...),
    display_name: Optional[str] = Form(None),
    summarize: bool = Form(False),
    action_items: bool = Form(False),
    llm_model: Optional[str] = Form(None),
    prompt_summary_id: Optional[int] = Form(None),
    prompt_action_items_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
) -> UploadCreateResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    ensure_dir(settings.upload_dir)

    # Create upload DB row first so we have an ID for storage path.
    name = (display_name or file.filename).strip()
    if not name:
        name = file.filename

    u = Upload(
        original_filename=file.filename,
        display_name=name,
        stored_path="",
        content_type=file.content_type,
        size_bytes=None,
    )
    db.add(u)
    db.commit()
    db.refresh(u)

    # Save file to /uploads/<id>/<uuid>.<ext>
    upload_dir = os.path.join(settings.upload_dir, str(u.id))
    ensure_dir(upload_dir)
    stored_name = safe_filename(file.filename)
    stored_path = os.path.join(upload_dir, stored_name)

    size = 0
    with open(stored_path, "wb") as out:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            size += len(chunk)

    u.stored_path = stored_path
    u.size_bytes = size
    db.commit()

    # Validate prompt IDs if provided.
    if prompt_summary_id is not None:
        p = db.query(Prompt).filter(Prompt.id == prompt_summary_id, Prompt.kind == "summary").first()
        if not p:
            raise HTTPException(status_code=400, detail="Invalid prompt_summary_id")
    if prompt_action_items_id is not None:
        p = db.query(Prompt).filter(Prompt.id == prompt_action_items_id, Prompt.kind == "action_items").first()
        if not p:
            raise HTTPException(status_code=400, detail="Invalid prompt_action_items_id")

    job = Job(
        upload_id=u.id,
        status="queued",
        phase="chunking",
        progress=0,
        summarize=bool(summarize),
        generate_action_items=bool(action_items),
        llm_model=(llm_model or None),
        prompt_summary_id=prompt_summary_id,
        prompt_action_items_id=prompt_action_items_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    celery_app.send_task("worker.tasks.process_upload", args=[job.id])
    return UploadCreateResponse(upload_id=u.id, job_id=job.id)


@router.post("/{upload_id}/reprocess", response_model=UploadReprocessResponse)
def reprocess_upload(upload_id: int, req: UploadReprocessRequest, db: Session = Depends(get_db)) -> UploadReprocessResponse:
    u = db.query(Upload).filter(Upload.id == upload_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Upload not found")

    if not req.summarize and not req.action_items:
        raise HTTPException(status_code=400, detail="Select summarize and/or action_items")

    job = Job(
        upload_id=u.id,
        status="queued",
        phase="summarizing" if req.summarize else "action_items",
        progress=0,
        summarize=bool(req.summarize),
        generate_action_items=bool(req.action_items),
        llm_model=(req.llm_model or None),
        prompt_summary_id=None,
        prompt_action_items_id=None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    celery_app.send_task("worker.tasks.process_llm", args=[job.id])
    return UploadReprocessResponse(upload_id=u.id, job_id=job.id)

