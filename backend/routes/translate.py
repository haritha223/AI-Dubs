import os
import uuid
import shutil
import logging
import asyncio
import subprocess
from fastapi import APIRouter, BackgroundTasks, Request, HTTPException, Query, UploadFile, File, Form
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

async def run_dubbing_pipeline(
    task_id: str,
    target_language: str,
    base_url: str,
    youtube_url: str = None,
    pre_downloaded_video: str = None,
):
    """Executes the entire dubbing pipeline step-by-step."""
    task = tasks_db[task_id]
    task["status"] = "processing"
    
    task_temp_dir = os.path.join(settings.TEMP_DIR, task_id)
    os.makedirs(task_temp_dir, exist_ok=True)
    
    try:
        # Step 1: Download Video & Extract Audio (or use pre-uploaded video)
        task["progress_step"] = "downloading"
        audio_path = os.path.join(task_temp_dir, "audio.wav")

        if pre_downloaded_video:
            video_path = pre_downloaded_video
            logger.info(f"Task {task_id}: Using pre-uploaded video, extracting audio...")
            await asyncio.to_thread(
                lambda: subprocess.run([
                    'ffmpeg', '-y', '-i', video_path,
                    '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                    audio_path
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            )
        else:
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
        
        # Save assets (to S3 or locally) and get their URLs
        dubbed_video_name = f"{task_id}_{final_video_name}"
        original_video_name = f"{task_id}_original_video.mp4"
        original_audio_name = f"{task_id}_original_audio.wav"
        
        dubbed_video_url = await asyncio.to_thread(save_file, final_video_path, dubbed_video_name, base_url)
        original_video_url = await asyncio.to_thread(save_file, video_path, original_video_name, base_url)
        original_audio_url = await asyncio.to_thread(save_file, audio_path, original_audio_name, base_url)
        
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
        await run_dubbing_pipeline(task_id, body.target_language, base_url, youtube_url=body.youtube_url)
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
        background_tasks.add_task(
            run_dubbing_pipeline, task_id, body.target_language, base_url, youtube_url=body.youtube_url
        )
        return {
            "task_id": task_id,
            "status": "queued",
            "message": "Translation task has been successfully scheduled in the background."
        }


@router.post("/upload-translate")
async def upload_translate(
    request: Request,
    background_tasks: BackgroundTasks,
    video: UploadFile = File(..., description="Video file to dub (mp4, mov, avi, mkv)"),
    target_language: str = Form(..., description="Target dubbing language"),
):
    """
    Accepts a local video file upload and starts the dubbing pipeline.
    Skips the YouTube download step entirely — useful when YouTube blocks EC2 IPs.
    """
    task_id = str(uuid.uuid4())
    task_temp_dir = os.path.join(settings.TEMP_DIR, task_id)
    os.makedirs(task_temp_dir, exist_ok=True)

    # Save uploaded video to temp dir
    video_path = os.path.join(task_temp_dir, "video.mp4")
    try:
        with open(video_path, "wb") as f:
            shutil.copyfileobj(video.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded video: {e}")
    finally:
        await video.close()

    # Register task
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
    background_tasks.add_task(
        run_dubbing_pipeline, task_id, target_language, base_url, pre_downloaded_video=video_path
    )
    return {
        "task_id": task_id,
        "status": "queued",
        "message": "Upload received. Dubbing pipeline started."
    }

@router.get("/translate/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Retrieves the status and progress of a dubbing task by ID."""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_db[task_id]
