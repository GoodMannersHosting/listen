from __future__ import annotations

from celery import Celery

from app.config import settings


celery_app = Celery(
    "listen",
    broker=settings.rabbitmq_url,
    backend=None,
)

celery_app.conf.update(
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

