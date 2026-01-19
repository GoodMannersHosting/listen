from __future__ import annotations

import json
import math
import os
import subprocess
from dataclasses import dataclass
from typing import Optional

from faster_whisper import WhisperModel

from app.config import settings


@dataclass
class Segment:
    start: float
    end: float
    text: str


def _run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or f"command failed: {' '.join(cmd)}")


def normalize_to_wav(input_path: str, output_path: str) -> None:
    _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            input_path,
            "-ac",
            "1",
            "-ar",
            "16000",
            "-vn",
            output_path,
        ]
    )


def chunk_wav(input_wav: str, chunk_dir: str, chunk_seconds: int) -> list[str]:
    os.makedirs(chunk_dir, exist_ok=True)
    pattern = os.path.join(chunk_dir, "chunk-%05d.wav")
    _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            input_wav,
            "-f",
            "segment",
            "-segment_time",
            str(chunk_seconds),
            "-reset_timestamps",
            "1",
            pattern,
        ]
    )
    files = sorted([os.path.join(chunk_dir, f) for f in os.listdir(chunk_dir) if f.startswith("chunk-") and f.endswith(".wav")])
    return files


_MODEL: WhisperModel | None = None


def get_model() -> WhisperModel:
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    # Try GPU then CPU fallback.
    try:
        _MODEL = WhisperModel(settings.whisper_model, device="cuda", compute_type="float16")
        return _MODEL
    except Exception:
        _MODEL = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
        return _MODEL


def transcribe_chunk(
    chunk_path: str,
) -> tuple[str, list[Segment], Optional[str]]:
    model = get_model()
    segments, info = model.transcribe(chunk_path, vad_filter=True)
    language: Optional[str] = getattr(info, "language", None) or None

    out_segments: list[Segment] = []
    texts: list[str] = []
    for seg in segments:
        s = Segment(
            start=float(seg.start),
            end=float(seg.end),
            text=(seg.text or "").strip(),
        )
        if s.text:
            out_segments.append(s)
            texts.append(s.text)

    return " ".join(texts).strip(), out_segments, language

