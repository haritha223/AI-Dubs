import logging
import whisper
from backend.config import settings

logger = logging.getLogger(__name__)

def transcribe_audio(audio_path: str) -> dict:
    """
    Transcribes the audio file using the local Whisper model.
    
    Args:
        audio_path (str): Path to the WAV audio file.
        
    Returns:
        dict: A dictionary containing:
            - "language": Detected language code (e.g. "en", "hi")
            - "segments": List of dicts with keys "start", "end", "text"
    """
    model_name = settings.WHISPER_MODEL_NAME
    logger.info(f"Loading Whisper model '{model_name}'...")
    
    try:
        # Load whisper model (uses GPU if available, else CPU)
        model = whisper.load_model(model_name)
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        raise RuntimeError(f"Could not load Whisper model: {e}")
        
    logger.info(f"Transcribing audio file: {audio_path}")
    try:
        # task="transcribe" keeps text in the source language's native script.
        # Do NOT pass language= so Whisper auto-detects; this prevents
        # romanization (phonetic English) of non-Latin scripts like Hindi/Nepali.
        result = model.transcribe(audio_path, task="transcribe", verbose=False)
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        raise RuntimeError(f"Whisper transcription failed: {e}")

    detected_language = result.get("language", "en")
    logger.info(f"Whisper detected language: {detected_language}")

    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "start": float(seg.get("start", 0.0)),
            "end": float(seg.get("end", 0.0)),
            "text": seg.get("text", "").strip()
        })
        
    logger.info(f"Transcription completed. Extracted {len(segments)} segments.")
    return {
        "language": detected_language,
        "segments": segments
    }
