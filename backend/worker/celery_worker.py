from __future__ import annotations

# Import the app, then import tasks so they register.
from worker.celery_app import celery_app  # noqa: F401

import worker.tasks  # noqa: F401

