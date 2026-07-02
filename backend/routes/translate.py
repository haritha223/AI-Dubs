import os
import uuid
import shutil
import logging
import asyncio
from fastapi import APIRouter, BackgroundTasks, Request, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from backend.config import settings
from backend.services.downloader import download_youtube_video
from backend.services.transcriber import transcribe_audio
from backend.services.translator import translator_service
from backend.services.tts import generate_all_tts_chunks
from backend.services.sync_engine import build_synchronized_audio
from backend.services.video_merger import merge_audio_and_video
from backend.services.storage import save_file

logger = logging.getLogger(__name__)
router = APIRouter()

# Simple in-memory task database
tasks_db = {}

class TranslationRequest(BaseModel):
    youtube_url: str
    target_language: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress_step: str = ""
    error_message: str = ""
    original_transcript: list = []
    translated_transcript: list = []
    dubbed_video_url: str = ""
    original_video_url: str = ""
    original_audio_url: str = ""

def clean_temp_dir(task_id: str):
    """Deletes temporary task directory."""
    task_temp_dir = os.path.join(settings.TEMP_DIR, task_id)
    if os.path.exists(task_temp_dir):
        try:
            shutil.rmtree(task_temp_dir)
            logger.info(f"Cleaned up temporary directory for task {task_id}")
        except Exception as e:
            logger.warning(f"Failed to clean up temp dir {task_temp_dir}: {e}")

async def run_dubbing_pipeline(task_id: str, youtube_url: str, target_language: str, base_url: str):
    """Executes the entire dubbing pipeline step-by-step."""
    task = tasks_db[task_id]
    task["status"] = "processing"
    
    task_temp_dir = os.path.join(settings.TEMP_DIR, task_id)
    os.makedirs(task_temp_dir, exist_ok=True)
    
    try:
        # Step 1: Download Video & Extract Audio
        task["progress_step"] = "downloading"
        logger.info(f"Task {task_id}: Downloading YouTube video...")
        video_path, audio_path = await asyncio.to_thread(
            download_youtube_video, youtube_url, task_temp_dir
        )
        
        # Step 2: Transcribe Speech-to-Text
        task["progress_step"] = "transcribing"
        logger.info(f"Task {task_id}: Transcribing audio...")
        transcription_result = await asyncio.to_thread(transcribe_audio, audio_path)
        source_lang = transcription_result["language"]
        segments = transcription_result["segments"]
        task["original_transcript"] = segments
        
        if not segments:
            raise ValueError("No speech segments detected in the video.")
            
        # Step 3: Translate Transcript using NLLB-200
        task["progress_step"] = "translating"
        logger.info(f"Task {task_id}: Translating segments from {source_lang} to {target_language}...")
        translated_segments = await asyncio.to_thread(
            translator_service.translate_segments, segments, source_lang, target_language
        )
        task["translated_transcript"] = translated_segments
        
        # Step 4: Text-to-Speech Generation
        task["progress_step"] = "tts_generation"
        logger.info(f"Task {task_id}: Generating voice chunks...")
        tts_chunks_dir = os.path.join(task_temp_dir, "tts_chunks")
        chunk_paths = await generate_all_tts_chunks(
            translated_segments, tts_chunks_dir, target_language
        )
        
        # Step 5: Timeline Synchronization
        task["progress_step"] = "synchronizing"
        logger.info(f"Task {task_id}: Synchronizing audio timeline...")
        sync_audio_path = await asyncio.to_thread(
            build_synchronized_audio, translated_segments, chunk_paths, video_path, task_temp_dir
        )
        
        # Step 6: Audio Video Merging
        task["progress_step"] = "merging"
        logger.info(f"Task {task_id}: Merging dubbed audio with video stream...")
        final_video_name = "dubbed_video.mp4"
        final_video_path = os.path.join(task_temp_dir, final_video_name)
        merge_audio_and_video(video_path, sync_audio_path, final_video_path)
        
        # Step 7: Asset Upload / Save
        task["progress_step"] = "uploading"
        logger.info(f"Task {task_id}: Uploading/saving generated assets...")
        
        # Save assets locally in outputs/ and construct URLs
        dubbed_video_name = f"{task_id}_{final_video_name}"
        original_video_name = f"{task_id}_original_video.mp4"
        original_audio_name = f"{task_id}_original_audio.wav"
        
        await asyncio.to_thread(save_file, final_video_path, dubbed_video_name)
        await asyncio.to_thread(save_file, video_path, original_video_name)
        await asyncio.to_thread(save_file, audio_path, original_audio_name)
        
        cleaned_base = base_url.rstrip('/')
        dubbed_video_url = f"{cleaned_base}/outputs/{dubbed_video_name}"
        original_video_url = f"{cleaned_base}/outputs/{original_video_name}"
        original_audio_url = f"{cleaned_base}/outputs/{original_audio_name}"
        
        # Update task with final URLs
        task["dubbed_video_url"] = dubbed_video_url
        task["original_video_url"] = original_video_url
        task["original_audio_url"] = original_audio_url
        
        task["status"] = "completed"
        task["progress_step"] = "completed"
        logger.info(f"Task {task_id} completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in task {task_id} pipeline: {e}", exc_info=True)
        task["status"] = "failed"
        task["error_message"] = str(e)
        
    finally:
        # Delete temporary working files
        clean_temp_dir(task_id)

@router.post("/translate")
async def start_translation(
    request: Request,
    body: TranslationRequest,
    background_tasks: BackgroundTasks,
    blocking: bool = Query(False, description="Run synchronously and block until completed")
):
    """
    Starts the video translation and dubbing process.
    If blocking is True, waits for pipeline to finish and returns final result.
    If blocking is False (default), starts background job and returns task_id.
    """
    task_id = str(uuid.uuid4())
    
    # Store initial state
    tasks_db[task_id] = {
        "task_id": task_id,
        "status": "queued",
        "progress_step": "queued",
        "error_message": "",
        "original_transcript": [],
        "translated_transcript": [],
        "dubbed_video_url": "",
        "original_video_url": "",
        "original_audio_url": ""
    }
    
    base_url = str(request.base_url)
    
    if blocking:
        # Run synchronously (blocking the request thread)
        await run_dubbing_pipeline(task_id, body.youtube_url, body.target_language, base_url)
        task_data = tasks_db[task_id]
        if task_data["status"] == "failed":
            raise HTTPException(status_code=500, detail=task_data["error_message"])
        return {
            "original_transcript": task_data["original_transcript"],
            "translated_transcript": task_data["translated_transcript"],
            "dubbed_video_url": task_data["dubbed_video_url"],
            "status": "success"
        }
    else:
        # Run asynchronously as a FastAPI Background Task
        background_tasks.add_task(
            run_dubbing_pipeline, task_id, body.youtube_url, body.target_language, base_url
        )
        return {
            "task_id": task_id,
            "status": "queued",
            "message": "Translation task has been successfully scheduled in the background."
        }

@router.get("/translate/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Retrieves the status and progress of a dubbing task by ID."""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_db[task_id]
