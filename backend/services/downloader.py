import os
import re
import subprocess
import logging
import requests
import yt_dlp

logger = logging.getLogger(__name__)

COBALT_API = "https://api.cobalt.tools/"
COOKIES_PATH = '/home/ubuntu/cookies.txt'


def _clean_youtube_url(url: str) -> str:
    """Return a clean youtube.com/watch?v=ID URL, stripping tracking params."""
    match = re.search(r'(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})', url)
    if match:
        return f'https://www.youtube.com/watch?v={match.group(1)}'
    return url


def _extract_audio(video_path: str, audio_path: str) -> None:
    """Extract mono 16kHz WAV audio from video using FFmpeg."""
    cmd = [
        'ffmpeg', '-y', '-i', video_path,
        '-vn',
        '-acodec', 'pcm_s16le',
        '-ar', '16000',
        '-ac', '1',
        audio_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _ensure_mp4(output_dir: str, video_path: str) -> str:
    """Scan output dir and rename/remux to video.mp4 if needed."""
    if os.path.exists(video_path):
        return video_path

    files = os.listdir(output_dir)
    video_files = [f for f in files if f.startswith("video.") and f.endswith((".mp4", ".mkv", ".webm"))]
    if not video_files:
        raise FileNotFoundError("Video file was not found after download.")

    downloaded_file = os.path.join(output_dir, video_files[0])
    if not downloaded_file.endswith(".mp4"):
        logger.info(f"Remuxing {downloaded_file} → MP4")
        subprocess.run(
            ['ffmpeg', '-y', '-i', downloaded_file, '-c:v', 'copy', '-c:a', 'aac', video_path],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        os.remove(downloaded_file)
    else:
        os.rename(downloaded_file, video_path)
    return video_path


def _download_via_cobalt(url: str, video_path: str) -> bool:
    """
    Try to download via cobalt.tools API.
    Returns True on success, False on failure (so caller can fall back).
    cobalt.tools runs on residential IPs — bypasses YouTube bot detection.
    """
    try:
        clean_url = _clean_youtube_url(url)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; AI-Dubs/1.0)",
        }
        # Minimal payload — only url is required by cobalt
        payload = {"url": clean_url}
        logger.info("Attempting download via cobalt.tools API...")
        resp = requests.post(COBALT_API, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        status = data.get("status", "")
        logger.info(f"cobalt.tools response status: {status}")

        if status in ("redirect", "tunnel", "stream"):
            dl_url = data.get("url")
            if not dl_url:
                logger.warning("cobalt.tools returned no URL")
                return False

            logger.info("Streaming video from cobalt.tools...")
            with requests.get(dl_url, stream=True, timeout=180) as r:
                r.raise_for_status()
                with open(video_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)

            if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                logger.info(f"cobalt.tools download succeeded: {video_path}")
                return True
            logger.warning("cobalt.tools download produced empty file")
            return False

        logger.warning(f"cobalt.tools unexpected status: {data}")
        return False

    except Exception as e:
        logger.warning(f"cobalt.tools download failed: {e}")
        return False


def _download_via_ytdlp(url: str, output_dir: str) -> None:
    """
    Fall back to yt-dlp.
    Uses tv_embedded player client — this client does NOT require PO tokens
    and works on server/datacenter IPs.
    """
    clean_url = _clean_youtube_url(url)
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': os.path.join(output_dir, 'video.%(ext)s'),
        'merge_output_format': 'mp4',
        'quiet': False,
        'no_warnings': False,
        'retries': 5,
        'socket_timeout': 60,
        # tv_embedded: server-safe client, no PO token required
        'extractor_args': {
            'youtube': {
                'player_client': ['tv_embedded'],
                'skip': ['dash', 'hls'],
            }
        },
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }

    if os.path.exists(COOKIES_PATH):
        ydl_opts['cookiefile'] = COOKIES_PATH
        logger.info(f"yt-dlp: using cookies from {COOKIES_PATH}")

    logger.info("Attempting download via yt-dlp (tv_embedded client)...")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([clean_url])


def download_youtube_video(url: str, output_dir: str) -> tuple[str, str]:
    """
    Downloads a YouTube video and extracts its audio.

    Strategy:
      1. Try cobalt.tools API (bypasses YouTube bot detection on datacenter IPs).
      2. Fall back to yt-dlp with cookies.

    Args:
        url: YouTube video URL.
        output_dir: Directory to save files.

    Returns:
        (video_path, audio_path) — paths to the MP4 and WAV files.
    """
    os.makedirs(output_dir, exist_ok=True)
    video_path = os.path.join(output_dir, "video.mp4")
    audio_path = os.path.join(output_dir, "audio.wav")

    # Remove stale files
    for path in [video_path, audio_path]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                logger.warning(f"Could not remove {path}: {e}")

    logger.info(f"Downloading video: {url}")

    # 1️⃣  Try cobalt.tools
    cobalt_ok = _download_via_cobalt(url, video_path)

    # 2️⃣  Fall back to yt-dlp
    if not cobalt_ok:
        logger.info("cobalt.tools unavailable — falling back to yt-dlp")
        try:
            _download_via_ytdlp(url, output_dir)
        except Exception as e:
            logger.error(f"yt-dlp download failed: {e}")
            raise ValueError(f"Failed to download YouTube video. Please check the URL: {e}")

    # Ensure we have video.mp4
    video_path = _ensure_mp4(output_dir, video_path)

    # Extract audio for Whisper
    logger.info("Extracting audio from video...")
    try:
        _extract_audio(video_path, audio_path)
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg audio extraction failed: {e}")
        raise RuntimeError(f"FFmpeg failed to extract audio: {e}")

    logger.info("Download and audio extraction complete.")
    return video_path, audio_path
