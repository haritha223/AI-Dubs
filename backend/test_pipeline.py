import os
import shutil
import asyncio
import logging
from backend.config import settings
from backend.services.downloader import download_youtube_video
from backend.services.transcriber import transcribe_audio
from backend.services.translator import translator_service
from backend.services.tts import generate_all_tts_chunks
from backend.services.sync_engine import build_synchronized_audio
from backend.services.video_merger import merge_audio_and_video

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

async def main():
    # Use a short, public domain or extremely short youtube video for testing
    # This is a 10-second test video
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw" 
    target_language = "Tamil"
    task_id = "test_run"
    
    test_dir = os.path.join(settings.TEMP_DIR, task_id)
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)
    
    logger.info("=== STEP 1: DOWNLOADING VIDEO ===")
    video_path, audio_path = download_youtube_video(test_url, test_dir)
    logger.info(f"Video saved to: {video_path}")
    logger.info(f"Audio saved to: {audio_path}")
    
    logger.info("=== STEP 2: TRANSCRIBING AUDIO ===")
    transcription = transcribe_audio(audio_path)
    logger.info(f"Detected language: {transcription['language']}")
    logger.info(f"Original segments:")
    for seg in transcription['segments']:
        logger.info(f"[{seg['start']:.2f}s - {seg['end']:.2f}s]: {seg['text']}")
        
    logger.info("=== STEP 3: TRANSLATING SEGMENTS ===")
    translated_segments = translator_service.translate_segments(
        transcription['segments'], 
        transcription['language'], 
        target_language
    )
    logger.info("Translated segments:")
    for seg in translated_segments:
        logger.info(f"[{seg['start']:.2f}s - {seg['end']:.2f}s]: {seg['text']} (Original: {seg['original_text']})")
        
    logger.info("=== STEP 4: GENERATING TTS CHUNKS ===")
    tts_chunks_dir = os.path.join(test_dir, "tts_chunks")
    chunk_paths = await generate_all_tts_chunks(
        translated_segments, 
        tts_chunks_dir, 
        target_language
    )
    logger.info(f"Generated {len(chunk_paths)} TTS chunks.")
    
    logger.info("=== STEP 5: SYNCHRONIZING TIMELINE ===")
    synchronized_audio_path = build_synchronized_audio(
        translated_segments, 
        chunk_paths, 
        video_path, 
        test_dir
    )
    logger.info(f"Synchronized audio saved to: {synchronized_audio_path}")
    
    logger.info("=== STEP 6: MERGING VIDEO & AUDIO ===")
    output_video_path = os.path.join(test_dir, "test_dubbed_video.mp4")
    merge_audio_and_video(video_path, synchronized_audio_path, output_video_path)
    logger.info(f"Final dubbed video saved to: {output_video_path}")
    
    logger.info("=== TEST PIPELINE RUN COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(main())
