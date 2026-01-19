"""Parakeet V3 transcription implementation."""
import torch
from transformers import pipeline
from typing import List, Tuple
from config import settings
from transcriber import TranscriberBase, TranscriptResult, TranscriptSegment


class ParakeetTranscriber(TranscriberBase):
    """Parakeet V3 transcription service."""
    
    def __init__(self):
        """Initialize Parakeet model."""
        model_name = settings.parakeet_model
        device = 0 if torch.cuda.is_available() else -1
        
        self.asr_pipeline = pipeline(
            "automatic-speech-recognition",
            model=model_name,
            device=device
        )
    
    def transcribe(self, audio_path: str) -> TranscriptResult:
        """Transcribe a single audio file."""
        result = self.asr_pipeline(audio_path, return_timestamps=True)
        
        text = result.get("text", "")
        chunks = result.get("chunks", [])
        
        segments = []
        for chunk in chunks:
            timestamp = chunk.get("timestamp", [0.0, 0.0])
            segments.append(
                TranscriptSegment(
                    text=chunk.get("text", ""),
                    start=timestamp[0] if isinstance(timestamp, list) else 0.0,
                    end=timestamp[1] if isinstance(timestamp, list) else 0.0,
                    confidence=None  # Parakeet may not provide confidence
                )
            )
        
        return TranscriptResult(
            text=text,
            segments=segments,
            language=None  # Parakeet auto-detects but doesn't return explicitly
        )
    
    def transcribe_chunks(self, chunk_paths: List[Tuple[str, float, float]]) -> TranscriptResult:
        """Transcribe multiple chunks and combine results."""
        all_segments = []
        full_text_parts = []
        
        for chunk_path, start_offset, end_offset in chunk_paths:
            result = self.asr_pipeline(chunk_path, return_timestamps=True)
            
            text = result.get("text", "")
            chunks = result.get("chunks", [])
            
            # Adjust segment timestamps by start_offset
            for chunk in chunks:
                timestamp = chunk.get("timestamp", [0.0, 0.0])
                seg_start = (timestamp[0] if isinstance(timestamp, list) else 0.0) + start_offset
                seg_end = (timestamp[1] if isinstance(timestamp, list) else 0.0) + start_offset
                
                all_segments.append(
                    TranscriptSegment(
                        text=chunk.get("text", ""),
                        start=seg_start,
                        end=seg_end,
                        confidence=None
                    )
                )
            
            full_text_parts.append(text)
        
        # Combine text with spaces
        full_text = " ".join(full_text_parts)
        
        return TranscriptResult(
            text=full_text,
            segments=all_segments,
            language=None
        )
