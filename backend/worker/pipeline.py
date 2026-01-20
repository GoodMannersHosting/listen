from __future__ import annotations

import ctypes
import json
import logging
import math
import os
import subprocess
from dataclasses import dataclass
from typing import Optional

from faster_whisper import WhisperModel

from app.config import settings

logger = logging.getLogger(__name__)


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
_MODEL_DEVICE: str | None = None


def _cuda_libs_available() -> bool:
    # If these libs are missing, faster-whisper will crash at runtime like:
    # "RuntimeError: Library libcublas.so.12 is not found or cannot be loaded"
    for lib in ("libcublas.so.12", "libcublas.so.11", "libcublas.so"):
        try:
            ctypes.CDLL(lib)
            return True
        except OSError:
            continue
    return False


def _pick_device() -> str:
    requested = (settings.whisper_device or "auto").strip().lower()
    if requested in ("cpu",):
        return "cpu"
    if requested in ("cuda", "gpu"):
        return "cuda"

    # auto: only attempt cuda if the pod/container looks GPU-enabled AND the CUDA libs are loadable.
    cuda_visible = (os.environ.get("CUDA_VISIBLE_DEVICES") or "").strip().lower()
    gpu_hint = bool(cuda_visible and cuda_visible not in ("-1", "none", "void"))
    gpu_dev = any(
        os.path.exists(p)
        for p in (
            "/dev/nvidiactl",
            "/dev/nvidia0",
            "/dev/nvidia1",
            "/dev/nvidia-uvm",
        )
    )
    if (gpu_hint or gpu_dev) and _cuda_libs_available():
        return "cuda"
    return "cpu"


def _build_model(device: str) -> WhisperModel:
    if device == "cuda":
        return WhisperModel(settings.whisper_model, device="cuda", compute_type="float16")
    return WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")


def get_model() -> WhisperModel:
    global _MODEL, _MODEL_DEVICE
    if _MODEL is not None:
        return _MODEL

    device = _pick_device()
    try:
        _MODEL = _build_model(device)
        _MODEL_DEVICE = device
        return _MODEL
    except Exception as e:
        logger.warning("Failed to init whisper model on %s: %s. Falling back to CPU.", device, e)
        _MODEL = _build_model("cpu")
        _MODEL_DEVICE = "cpu"
        return _MODEL


def transcribe_chunk(
    chunk_path: str,
) -> tuple[str, list[Segment], Optional[str]]:
    global _MODEL, _MODEL_DEVICE
    model = get_model()
    try:
        segments, info = model.transcribe(chunk_path, vad_filter=True)
    except RuntimeError as e:
        # Some environments let WhisperModel(device="cuda") initialize, but fail later when CUDA libs are missing.
        msg = str(e).lower()
        if _MODEL_DEVICE == "cuda" and ("libcublas" in msg or "cublas" in msg or "cuda" in msg):
            logger.warning("CUDA runtime error (%s). Retrying transcription on CPU.", e)
            _MODEL = _build_model("cpu")
            _MODEL_DEVICE = "cpu"
            segments, info = _MODEL.transcribe(chunk_path, vad_filter=True)
        else:
            raise
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

