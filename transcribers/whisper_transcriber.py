"""Whisper transcription implementation."""
import warnings
import whisper
from typing import List, Tuple
from config import settings
from transcriber import TranscriberBase, TranscriptResult, TranscriptSegment

# Suppress FP16 CPU warning (it's expected behavior)
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")


class WhisperTranscriber(TranscriberBase):
    """Whisper transcription service."""
    
    def __init__(self):
        """Initialize Whisper transcriber (model loaded lazily)."""
        self.model_size = settings.whisper_model
        self.model = None
    
    def _get_model(self):
        """Lazy-load the Whisper model."""
        if self.model is None:
            self.model = whisper.load_model(self.model_size)
        return self.model
    
    def transcribe(self, audio_path: str) -> TranscriptResult:
        """Transcribe a single audio file."""
        model = self._get_model()
        result = model.transcribe(audio_path)
        
        segments = []
        for seg in result.get("segments", []):
            segments.append(
                TranscriptSegment(
                    text=seg.get("text", ""),
                    start=seg.get("start", 0.0),
                    end=seg.get("end", 0.0),
                    confidence=None  # Whisper doesn't provide confidence scores directly
                )
            )
        
        return TranscriptResult(
            text=result.get("text", ""),
            segments=segments,
            language=result.get("language", None)
        )
    
    def transcribe_chunks(self, chunk_paths: List[Tuple[str, float, float]]) -> TranscriptResult:
        """Transcribe multiple chunks and combine results."""
        model = self._get_model()
        all_segments = []
        full_text_parts = []
        language = None
        
        for chunk_path, start_offset, end_offset in chunk_paths:
            result = model.transcribe(chunk_path)
            
            if language is None:
                language = result.get("language", None)
            
            # Adjust segment timestamps by start_offset
            for seg in result.get("segments", []):
                seg_start = seg.get("start", 0.0) + start_offset
                seg_end = seg.get("end", 0.0) + start_offset
                all_segments.append(
                    TranscriptSegment(
                        text=seg.get("text", ""),
                        start=seg_start,
                        end=seg_end,
                        confidence=None
                    )
                )
            
            full_text_parts.append(result.get("text", ""))
        
        # Combine text with spaces
        full_text = " ".join(full_text_parts)
        
        return TranscriptResult(
            text=full_text,
            segments=all_segments,
            language=language
        )
