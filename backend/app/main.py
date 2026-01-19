from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import db_healthcheck, engine
from app.models import Base, Prompt
from app.routes.jobs import router as jobs_router
from app.routes.prompts import router as prompts_router
from app.routes.uploads import router as uploads_router


def _load_default_prompts() -> None:
    prompt_dir = Path(__file__).resolve().parent.parent / "prompts"
    defaults = [
        ("Default Summary Prompt", "summary", prompt_dir / "summary_default.md"),
        ("Default Action Items Prompt", "action_items", prompt_dir / "action_items_default.md"),
    ]

    legacy_default_summary_v1 = """You are an assistant that summarizes meeting transcripts.

Write a concise, structured summary with:
- Key points (bullets)
- Decisions
- Open questions
- Risks

Be factual and do not invent details.
"""

    def _norm(s: str) -> str:
        return (s or "").strip().replace("\r\n", "\n").replace("\r", "\n")

    from sqlalchemy.orm import Session

    with Session(engine) as db:
        for name, kind, path in defaults:
            content = path.read_text(encoding="utf-8") if path.exists() else ""
            p = db.query(Prompt).filter(Prompt.name == name, Prompt.kind == kind).first()
            if not p:
                db.add(Prompt(name=name, kind=kind, content=content, is_default=True))
                continue

            # Update shipped defaults only if the user hasn't edited them.
            # If a user has customized prompt content, we leave it alone.
            if not p.is_default:
                continue

            # If the DB still has the legacy v1 summary prompt, upgrade it.
            if kind == "summary" and name == "Default Summary Prompt" and _norm(p.content) == _norm(legacy_default_summary_v1):
                p.content = content
        db.commit()


def create_app() -> FastAPI:
    os.makedirs(settings.upload_dir, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _load_default_prompts()

    app = FastAPI(title="Listen API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def healthz():
        return {"ok": True, "db": db_healthcheck()}

    app.include_router(uploads_router, prefix="/api")
    app.include_router(jobs_router, prefix="/api")
    app.include_router(prompts_router, prefix="/api")

    return app


app = create_app()

