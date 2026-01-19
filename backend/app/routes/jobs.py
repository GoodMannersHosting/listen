from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Job
from app.schemas import JobStats, JobStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/stats", response_model=JobStats)
def get_job_stats(db: Session = Depends(get_db)) -> JobStats:
    queued = db.query(Job).filter(Job.status == "queued").count()
    processing = db.query(Job).filter(Job.status == "processing").count()
    return JobStats(queued=queued, processing=processing, active=queued + processing)


@router.get("/active", response_model=list[JobStatus])
def list_active_jobs(db: Session = Depends(get_db)) -> list[JobStatus]:
    jobs = (
        db.query(Job)
        .filter(Job.status.in_(["queued", "processing"]))
        .order_by(Job.created_at.asc())
        .all()
    )
    return [
        JobStatus(
            id=j.id,
            upload_id=j.upload_id,
            status=j.status,
            phase=j.phase,
            progress=j.progress,
            total_chunks=j.total_chunks,
            current_chunk=j.current_chunk,
            error=j.error,
            created_at=j.created_at,
            started_at=j.started_at,
            finished_at=j.finished_at,
        )
        for j in jobs
    ]


@router.get("/{job_id}", response_model=JobStatus)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobStatus:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(
        id=job.id,
        upload_id=job.upload_id,
        status=job.status,
        phase=job.phase,
        progress=job.progress,
        total_chunks=job.total_chunks,
        current_chunk=job.current_chunk,
        error=job.error,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )

