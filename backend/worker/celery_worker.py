from __future__ import annotations

# Import the app, then import tasks so they register.
from worker.celery_app import celery_app  # noqa: F401

from app.db import ensure_schema

ensure_schema()

import worker.tasks  # noqa: F401

