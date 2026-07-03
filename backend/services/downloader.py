import os
import subprocess
import logging
import yt_dlp
from pathlib import Path

logger = logging.getLogger(__name__)

def download_youtube_video(url: str, output_dir: str) -> tuple[str, str]:
    """
    Downloads a YouTube video and extracts its audio.
    
    Args:
        url (str): The YouTube video URL.
        output_dir (str): Directory to save downloaded files.
        
    Returns:
        tuple[str, str]: Paths to the downloaded video (MP4) and extracted audio (WAV).
    """
    os.makedirs(output_dir, exist_ok=True)
    video_path = os.path.join(output_dir, "video.mp4")
    audio_path = os.path.join(output_dir, "audio.wav")
    
    # Clean previous files if they exist
    for path in [video_path, audio_path]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                logger.warning(f"Could not remove existing file {path}: {e}")

    logger.info(f"Downloading video from: {url}")
    
    # yt-dlp options
    # NOTE: Use a fully static output path ('video.mp4') to avoid [Errno 22]
    # Invalid argument on Windows — yt-dlp's default template embeds the video
    # title which may contain characters Windows rejects in filenames.
    # Use cookies file if available
    cookies_path = '/home/ubuntu/cookies.txt'
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        # Static filename — avoids Windows [Errno 22] from special chars in title
        'outtmpl': os.path.join(output_dir, 'video.%(ext)s'),
        'merge_output_format': 'mp4',
        # Sanitize filenames for Windows (replaces forbidden characters)
        'windows_filenames': True,
        'quiet': False,
        'no_warnings': False,
        'retries': 5,
        'socket_timeout': 30,
        # Use ios client — bypasses bot detection on server environments
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'tv_embedded'],
            }
        },
        'http_headers': {
            'User-Agent': (
                'com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X)'
            ),
        },
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }
    
    # Add cookies if file exists
    if os.path.exists(cookies_path):
        ydl_opts['cookiefile'] = cookies_path
        logger.info(f"Using cookies from {cookies_path}")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        logger.error(f"yt-dlp download failed: {e}")
        raise ValueError(f"Failed to download YouTube video. Please check the URL: {e}")

    # Verify video was downloaded (yt-dlp might have saved it under another extension or merged correctly)
    if not os.path.exists(video_path):
        # Scan output directory for any video files and rename/move to video.mp4
        files = os.listdir(output_dir)
        video_files = [f for f in files if f.startswith("video.") and f.endswith((".mp4", ".mkv", ".webm"))]
        if video_files:
            downloaded_file = os.path.join(output_dir, video_files[0])
            # If it's not mp4, we let ffmpeg transcode it during audio extraction, 
            # but we also rename/re-encode it to video.mp4
            if not downloaded_file.endswith(".mp4"):
                logger.info(f"Remuxing {downloaded_file} to MP4")
                try:
                    subprocess.run([
                        'ffmpeg', '-y', '-i', downloaded_file,
                        '-c:v', 'copy', '-c:a', 'aac', video_path
                    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    os.remove(downloaded_file)
                except Exception as ex:
                    logger.error(f"Remux to MP4 failed: {ex}")
                    raise ValueError(f"Could not convert downloaded video to MP4 format: {ex}")
            else:
                os.rename(downloaded_file, video_path)
        else:
            raise FileNotFoundError("Video file was not found after download.")

    logger.info("Extracting audio from video")
    # Extract mono WAV 16kHz audio for Whisper
    try:
        cmd = [
            'ffmpeg', '-y', '-i', video_path,
            '-vn',                    # No video
            '-acodec', 'pcm_s16le',   # PCM 16-bit
            '-ar', '16000',           # 16kHz sample rate
            '-ac', '1',               # Mono channel
            audio_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg audio extraction failed: {e}")
        raise RuntimeError(f"FFmpeg failed to extract audio from video: {e}")
        
    logger.info("Video download and audio extraction completed successfully")
    return video_path, audio_path
