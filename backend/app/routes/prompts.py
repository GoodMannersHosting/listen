from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Prompt
from app.schemas import PromptOut, PromptUpdateRequest

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("", response_model=list[PromptOut])
def list_prompts(db: Session = Depends(get_db)) -> list[PromptOut]:
    rows = db.query(Prompt).order_by(Prompt.kind.asc(), Prompt.is_default.desc(), Prompt.id.asc()).all()
    return [
        PromptOut(
            id=p.id,
            name=p.name,
            kind=p.kind,
            content=p.content,
            is_default=p.is_default,
            updated_at=p.updated_at,
        )
        for p in rows
    ]


@router.get("/{prompt_id}", response_model=PromptOut)
def get_prompt(prompt_id: int, db: Session = Depends(get_db)) -> PromptOut:
    p = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return PromptOut(
        id=p.id,
        name=p.name,
        kind=p.kind,
        content=p.content,
        is_default=p.is_default,
        updated_at=p.updated_at,
    )


@router.put("/{prompt_id}", response_model=PromptOut)
def update_prompt(prompt_id: int, req: PromptUpdateRequest, db: Session = Depends(get_db)) -> PromptOut:
    p = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if req.name is not None:
        p.name = req.name
    if req.content is not None:
        p.content = req.content
    if req.is_default is not None:
        if req.is_default:
            # ensure only one default per kind
            db.query(Prompt).filter(Prompt.kind == p.kind).update({Prompt.is_default: False})
        p.is_default = req.is_default

    db.commit()
    db.refresh(p)
    return PromptOut(
        id=p.id,
        name=p.name,
        kind=p.kind,
        content=p.content,
        is_default=p.is_default,
        updated_at=p.updated_at,
    )

