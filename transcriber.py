"""Transcription service abstraction."""
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
from config import settings


class TranscriptSegment:
    """Represents a transcript segment with timing information."""
    def __init__(self, text: str, start: float, end: float, confidence: float = None):
        self.text = text
        self.start = start
        self.end = end
        self.confidence = confidence


class TranscriptResult:
    """Represents the full transcription result."""
    def __init__(self, text: str, segments: List[TranscriptSegment] = None, language: str = None):
        self.text = text
        self.segments = segments or []
        self.language = language


class TranscriberBase(ABC):
    """Abstract base class for transcription backends."""
    
    @abstractmethod
    def transcribe(self, audio_path: str) -> TranscriptResult:
        """Transcribe an audio file."""
        pass
    
    @abstractmethod
    def transcribe_chunks(self, chunk_paths: List[Tuple[str, float, float]]) -> TranscriptResult:
        """
        Transcribe multiple audio chunks.
        
        Args:
            chunk_paths: List of (path, start_time, end_time) tuples
        
        Returns:
            Combined TranscriptResult
        """
        pass


def get_transcriber() -> TranscriberBase:
    """Factory function to get the configured transcriber."""
    model = settings.transcription_model.lower()
    
    if model == "whisper":
        from transcribers.whisper_transcriber import WhisperTranscriber
        return WhisperTranscriber()
    elif model == "parakeet":
        from transcribers.parakeet_transcriber import ParakeetTranscriber
        return ParakeetTranscriber()
    else:
        raise ValueError(f"Unknown transcription model: {model}. Supported: whisper, parakeet")
