"""Speaker diarization service using pyannote-audio."""
from typing import List, Dict, Tuple, Optional, Any
from config import settings
from pyannote.audio import Pipeline


class DiarizationService:
    """Speaker diarization service using pyannote-audio."""
    
    def __init__(self):
        """Initialize diarization pipeline."""
        if not settings.enable_diarization:
            self.pipeline = None
            return
        
        pipeline_name = f"pyannote/speaker-diarization-{settings.pyannote_pipeline}"
        try:
            self.pipeline = Pipeline.from_pretrained(pipeline_name)
            # Use exclusive speaker diarization mode if available
            if hasattr(self.pipeline, "exclusive"):
                self.pipeline.exclusive = True
        except Exception as e:
            print(f"Warning: Failed to load diarization pipeline: {e}")
            self.pipeline = None
    
    def is_enabled(self) -> bool:
        """Check if diarization is enabled and available."""
        return settings.enable_diarization and self.pipeline is not None
    
    def diarize(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Perform speaker diarization on audio file.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            List of speaker segments: [{"start": float, "end": float, "speaker": str}, ...]
        """
        if not self.is_enabled():
            return []
        
        try:
            diarization = self.pipeline(audio_path)
            segments = []
            
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append({
                    "start": turn.start,
                    "end": turn.end,
                    "speaker": speaker
                })
            
            return segments
        except Exception as e:
            print(f"Warning: Diarization failed: {e}")
            return []
    
    def align_speakers_to_transcript(
        self,
        transcript_segments: List[Dict[str, Any]],
        diarization_segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Align speaker labels from diarization with transcript segments.
        
        Args:
            transcript_segments: List of transcript segments with start/end times
            diarization_segments: List of diarization segments with speaker labels
            
        Returns:
            Transcript segments with speaker labels added
        """
        if not diarization_segments:
            return transcript_segments
        
        # Create a mapping of time to speaker
        speaker_map = []
        for seg in diarization_segments:
            speaker_map.append((seg["start"], seg["end"], seg["speaker"]))
        
        # Align each transcript segment with speakers
        aligned_segments = []
        for trans_seg in transcript_segments:
            seg_start = trans_seg.get("start_time", 0.0)
            seg_end = trans_seg.get("end_time", seg_start + 1.0)
            seg_mid = (seg_start + seg_end) / 2.0
            
            # Find which speaker is active at the midpoint of the segment
            speaker = None
            for diar_start, diar_end, diar_speaker in speaker_map:
                if diar_start <= seg_mid <= diar_end:
                    speaker = diar_speaker
                    break
            
            aligned_seg = trans_seg.copy()
            if speaker:
                aligned_seg["speaker_label"] = speaker
            
            aligned_segments.append(aligned_seg)
        
        return aligned_segments


def get_diarization_service() -> DiarizationService:
    """Get diarization service instance."""
    return DiarizationService()
