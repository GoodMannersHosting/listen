"""Audio processing utilities using python-ffmpeg."""
import os
import json
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional
from config import settings


def get_audio_duration(audio_path: str) -> float:
    """Get audio duration in seconds using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError) as e:
        raise ValueError(f"Failed to get audio duration: {e}")


def normalize_audio(input_path: str, output_path: str) -> str:
    """
    Normalize audio to 16kHz mono using FFmpeg.
    This is compatible with Whisper, Parakeet, and pyannote-audio.
    """
    try:
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-ar", "16000",  # Sample rate 16kHz
            "-ac", "1",      # Mono
            "-y",            # Overwrite output
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Failed to normalize audio: {e.stderr.decode() if e.stderr else str(e)}")


def chunk_audio(
    audio_path: str,
    chunk_duration: int = None,
    overlap: float = 0.0,
    output_dir: Optional[str] = None
) -> List[Tuple[str, float, float]]:
    """
    Split audio into chunks if longer than chunk_duration.
    
    Args:
        audio_path: Path to input audio file
        chunk_duration: Duration of each chunk in seconds (defaults to config value)
        overlap: Overlap between chunks in seconds (default 0)
        output_dir: Directory to save chunks (defaults to temp directory)
    
    Returns:
        List of tuples: (chunk_path, start_time, end_time)
    """
    if chunk_duration is None:
        chunk_duration = settings.audio_chunk_duration
    
    duration = get_audio_duration(audio_path)
    
    # If audio is shorter than chunk_duration, return single chunk
    if duration <= chunk_duration:
        normalized_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        normalized_path.close()
        normalize_audio(audio_path, normalized_path.name)
        return [(normalized_path.name, 0.0, duration)]
    
    # Create output directory
    if output_dir is None:
        output_dir = tempfile.mkdtemp()
    else:
        os.makedirs(output_dir, exist_ok=True)
    
    chunks = []
    start_time = 0.0
    chunk_index = 0
    
    while start_time < duration:
        end_time = min(start_time + chunk_duration, duration)
        
        # Calculate actual chunk duration (accounting for overlap)
        actual_end = end_time + overlap if end_time < duration else end_time
        
        chunk_path = os.path.join(output_dir, f"chunk_{chunk_index:04d}.wav")
        
        try:
            cmd = [
                "ffmpeg",
                "-i", audio_path,
                "-ss", str(start_time),
                "-t", str(actual_end - start_time),
                "-ar", "16000",  # Normalize to 16kHz
                "-ac", "1",      # Mono
                "-y",
                chunk_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            chunks.append((chunk_path, start_time, end_time))
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to create chunk {chunk_index}: {e}")
        
        # Move to next chunk (with overlap)
        start_time = end_time - overlap if overlap > 0 else end_time
        chunk_index += 1
    
    return chunks


def convert_audio_format(input_path: str, output_path: str, output_format: str = "wav") -> str:
    """Convert audio file to specified format using FFmpeg."""
    try:
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-y",
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Failed to convert audio format: {e.stderr.decode() if e.stderr else str(e)}")


def get_audio_info(audio_path: str) -> dict:
    """Get audio file information using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration,size,bit_rate",
            "-show_entries", "stream=sample_rate,channels,codec_name",
            "-of", "json",
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to get audio info: {e}")
