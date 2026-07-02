import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def get_media_duration(file_path: str) -> float:
    """Retrieves the duration of an audio or video file in seconds, falling back to ffmpeg -i if ffprobe is missing."""
    cmd = [
        'ffprobe', '-v', 'error', 
        '-show_entries', 'format=duration', 
        '-of', 'default=noprint_wrappers=1:nokey=1', 
        file_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception:
        pass # fallback to ffmpeg

    # Fallback to ffmpeg -i parsing
    import re
    cmd = ['ffmpeg', '-i', file_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        output = result.stderr
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", output)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = float(match.group(3))
            return hours * 3600 + minutes * 60 + seconds
    except Exception as e:
        logger.error(f"Failed to get duration of {file_path} using ffmpeg fallback: {e}")
        
    return 0.0

def generate_silence(duration: float, output_path: str) -> None:
    """Generates a silent WAV file of the specified duration at 44100Hz, stereo."""
    cmd = [
        'ffmpeg', '-y', 
        '-f', 'lavfi', 
        '-i', f'anullsrc=r=44100:cl=stereo', 
        '-t', f'{duration:.3f}', 
        '-ar', '44100', 
        '-ac', '2', 
        output_path
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg silence generation failed: {e}")
        raise RuntimeError(f"Failed to generate silence of {duration}s: {e}")

def normalize_and_speed_chunk(input_path: str, output_path: str, target_duration: float = None, max_speedup: float = 1.4) -> float:
    """
    Normalizes an audio chunk to 44100Hz, stereo, and optionally speeds it up 
    using the atempo filter to fit a target duration.
    
    Returns:
        float: The actual duration of the normalized chunk.
    """
    current_duration = get_media_duration(input_path)
    if current_duration == 0.0:
        current_duration = 0.1 # avoid division by zero

    speed_factor = 1.0
    if target_duration and current_duration > target_duration:
        # Calculate necessary speedup
        speed_factor = current_duration / target_duration
        # Clamp speedup factor to ensure speech is still legible
        speed_factor = min(speed_factor, max_speedup)
        
    # Build FFmpeg command to normalize format and speed up if needed
    cmd = ['ffmpeg', '-y', '-i', input_path]
    
    # Apply speedup using atempo filter if speed_factor is significantly > 1.0
    if speed_factor > 1.02:
        logger.info(f"Speeding up chunk {input_path} by {speed_factor:.2f}x to fit in slot")
        # atempo filter can be chained if it goes beyond 2.0, but we capped at 1.4, so single filter is fine
        cmd.extend(['-filter:a', f'atempo={speed_factor:.3f}'])
        
    cmd.extend([
        '-ar', '44100',  # 44.1kHz
        '-ac', '2',       # Stereo
        output_path
    ])
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg normalization/speedup failed for {input_path}: {e}")
        raise RuntimeError(f"Failed to normalize and speed up chunk {input_path}: {e}")
        
    # Return the actual duration of the finalized chunk
    return get_media_duration(output_path)

def build_synchronized_audio(segments: list[dict], chunk_paths: list[str], video_path: str, temp_dir: str) -> str:
    """
    Builds a single synchronized audio track by placing TTS chunks at their 
    respective timestamps, filling spaces with silence, and copying original timing structure.
    
    Args:
        segments (list[dict]): Original/translated segments metadata with "start", "end".
        chunk_paths (list[str]): Paths to the generated TTS chunk mp3 files.
        video_path (str): Path to the original video file (to determine full timeline length).
        temp_dir (str): Temporary directory to write work files.
        
    Returns:
        str: Path to the generated full_dubbed_audio.wav file.
    """
    logger.info("Starting audio timeline synchronization...")
    
    if len(segments) != len(chunk_paths):
        raise ValueError(f"Mismatch: segments count ({len(segments)}) does not match chunks count ({len(chunk_paths)})")
        
    sync_chunks_dir = os.path.join(temp_dir, "sync_chunks")
    os.makedirs(sync_chunks_dir, exist_ok=True)
    
    video_duration = get_media_duration(video_path)
    logger.info(f"Original video duration: {video_duration:.2f} seconds")
    
    timeline_files = []
    current_time = 0.0
    
    for i, (seg, chunk_path) in enumerate(zip(segments, chunk_paths)):
        start_time = seg["start"]
        end_time = seg["end"]
        
        # Calculate available duration for this chunk.
        # It can overlap slightly into the silence before the next chunk.
        # So the limit is the next chunk's start time, or the video duration, or segment end.
        if i < len(segments) - 1:
            limit = segments[i + 1]["start"] - start_time
        else:
            limit = max(end_time - start_time, video_duration - start_time)
            
        # 1. Insert Silence if there is a gap
        gap = start_time - current_time
        if gap > 0.05: # ignore negligible micro-gaps
            silence_path = os.path.join(sync_chunks_dir, f"silence_{i}.wav")
            generate_silence(gap, silence_path)
            timeline_files.append(silence_path)
            current_time += gap
            
        # 2. Normalize and potentially speed up the TTS chunk
        normalized_chunk_path = os.path.join(sync_chunks_dir, f"chunk_{i}_norm.wav")
        # Ensure it fits within the limit
        actual_chunk_duration = normalize_and_speed_chunk(
            input_path=chunk_path,
            output_path=normalized_chunk_path,
            target_duration=limit
        )
        
        timeline_files.append(normalized_chunk_path)
        current_time += actual_chunk_duration

    # 3. Add trailing silence if the video is longer than the audio timeline
    trailing_gap = video_duration - current_time
    if trailing_gap > 0.05:
        trailing_silence_path = os.path.join(sync_chunks_dir, "silence_trail.wav")
        generate_silence(trailing_gap, trailing_silence_path)
        timeline_files.append(trailing_silence_path)
        current_time += trailing_gap

    # 4. Concatenate all timeline files using the FFmpeg concat demuxer
    concat_file_list_path = os.path.join(temp_dir, "concat_list.txt")
    with open(concat_file_list_path, "w", encoding="utf-8") as f:
        for file_path in timeline_files:
            # Format: file '/path/to/file'
            # Escape single quotes and use forward slashes
            normalized_path = str(Path(file_path).absolute()).replace("\\", "/")
            f.write(f"file '{normalized_path}'\n")
            
    output_audio_path = os.path.join(temp_dir, "full_dubbed_audio.wav")
    
    logger.info(f"Concatenating {len(timeline_files)} audio files to {output_audio_path}")
    concat_cmd = [
        'ffmpeg', '-y', 
        '-f', 'concat', 
        '-safe', '0', 
        '-i', concat_file_list_path, 
        '-c', 'copy', 
        output_audio_path
    ]
    
    try:
        subprocess.run(concat_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg audio concatenation failed: {e}")
        raise RuntimeError(f"Failed to concatenate audio chunks: {e}")
        
    logger.info("Timeline audio synchronization completed successfully.")
    return output_audio_path
