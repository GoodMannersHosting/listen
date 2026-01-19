from __future__ import annotations

import os
import pathlib
import shutil
import uuid


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def safe_filename(name: str) -> str:
    # Keep extension, discard path separators.
    p = pathlib.Path(name)
    ext = p.suffix.lower()
    return f"{uuid.uuid4().hex}{ext}"


def delete_tree(path: str) -> None:
    if not path:
        return
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

