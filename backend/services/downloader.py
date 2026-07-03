import os
import re
import subprocess
import logging
import requests
import yt_dlp

logger = logging.getLogger(__name__)

COOKIES_PATH = '/home/ubuntu/cookies.txt'

# Public Invidious instances — these proxy YouTube and bypass IP blocks
INVIDIOUS_INSTANCES = [
    "https://yewtu.be",
    "https://inv.nadeko.net",
    "https://invidious.privacyredirect.com",
    "https://iv.melmac.space",
    "https://invidious.nerdvpn.de",
]

# cobalt.tools API
COBALT_API = "https://api.cobalt.tools/"


# ─── Helpers ────────────────────────────────────────────────────────────────

def _extract_video_id(url: str) -> str | None:
    match = re.search(r'(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})', url)
    return match.group(1) if match else None


def _clean_youtube_url(url: str) -> str:
    vid = _extract_video_id(url)
    return f'https://www.youtube.com/watch?v={vid}' if vid else url


def _extract_audio(video_path: str, audio_path: str) -> None:
    """Extract mono 16 kHz WAV audio from video using FFmpeg."""
    cmd = [
        'ffmpeg', '-y', '-i', video_path,
        '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
        audio_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _ensure_mp4(output_dir: str, video_path: str) -> str:
    if os.path.exists(video_path):
        return video_path
    files = os.listdir(output_dir)
    video_files = [f for f in files if f.startswith("video.") and f.endswith((".mp4", ".mkv", ".webm"))]
    if not video_files:
        raise FileNotFoundError("Video file was not found after download.")
    downloaded_file = os.path.join(output_dir, video_files[0])
    if not downloaded_file.endswith(".mp4"):
        subprocess.run(
            ['ffmpeg', '-y', '-i', downloaded_file, '-c:v', 'copy', '-c:a', 'aac', video_path],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        os.remove(downloaded_file)
    else:
        os.rename(downloaded_file, video_path)
    return video_path


def _stream_url_to_file(download_url: str, video_path: str) -> bool:
    """Download a direct video URL to disk. Returns True on success."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.youtube.com/",
        }
        with requests.get(download_url, stream=True, timeout=180, headers=headers) as r:
            r.raise_for_status()
            with open(video_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
        if os.path.exists(video_path) and os.path.getsize(video_path) > 100_000:
            return True
        logger.warning("Downloaded file is too small — treating as failure")
        if os.path.exists(video_path):
            os.remove(video_path)
        return False
    except Exception as e:
        logger.warning(f"Stream download failed: {e}")
        return False


# ─── Download strategies ─────────────────────────────────────────────────────

def _download_via_invidious(url: str, video_path: str) -> bool:
    """
    Use a public Invidious instance to get a direct video stream URL.
    Invidious acts as a YouTube proxy — no EC2 IP block.
    """
    video_id = _extract_video_id(url)
    if not video_id:
        return False

    headers = {"User-Agent": "Mozilla/5.0"}

    for instance in INVIDIOUS_INSTANCES:
        try:
            api_url = f"{instance}/api/v1/videos/{video_id}?fields=formatStreams,adaptiveFormats"
            logger.info(f"Trying Invidious: {instance}")
            resp = requests.get(api_url, headers=headers, timeout=20)
            if resp.status_code != 200:
                logger.warning(f"{instance} returned {resp.status_code}")
                continue

            data = resp.json()
            streams = data.get("formatStreams", [])  # combined audio+video
            adaptive = data.get("adaptiveFormats", [])

            # Prefer combined streams (formatStreams) — they include both audio & video
            candidates = [f for f in streams if "video/mp4" in f.get("type", "")]
            if not candidates:
                candidates = [f for f in streams if "video" in f.get("type", "")]
            if not candidates:
                # Fall back to adaptive video streams
                candidates = [f for f in adaptive if "video/mp4" in f.get("type", "") and "avc" in f.get("type", "")]

            if not candidates:
                logger.warning(f"{instance}: no suitable stream found")
                continue

            # Pick highest quality
            def _quality_key(f):
                q = f.get("quality", "0")
                return int(re.sub(r'\D', '', q) or 0)

            candidates.sort(key=_quality_key, reverse=True)
            dl_url = candidates[0].get("url")
            if not dl_url:
                continue

            logger.info(f"Downloading from {instance} — quality: {candidates[0].get('quality', '?')}")
            if _stream_url_to_file(dl_url, video_path):
                logger.info(f"Invidious download succeeded via {instance}")
                return True

        except Exception as e:
            logger.warning(f"Invidious {instance} error: {e}")
            continue

    return False


def _download_via_cobalt(url: str, video_path: str) -> bool:
    """Try cobalt.tools API (residential IP proxy for YouTube)."""
    try:
        clean_url = _clean_youtube_url(url)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; AI-Dubs/1.0)",
        }
        payload = {"url": clean_url}
        logger.info("Trying cobalt.tools API...")
        resp = requests.post(COBALT_API, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "")
        logger.info(f"cobalt status: {status}")

        if status in ("redirect", "tunnel", "stream"):
            dl_url = data.get("url")
            if dl_url and _stream_url_to_file(dl_url, video_path):
                logger.info("cobalt.tools download succeeded")
                return True

        logger.warning(f"cobalt.tools unexpected response: {data}")
        return False

    except Exception as e:
        logger.warning(f"cobalt.tools failed: {e}")
        return False


def _download_via_ytdlp(url: str, output_dir: str) -> None:
    """Last resort: yt-dlp with tv_embedded client (no PO token required)."""
    clean_url = _clean_youtube_url(url)
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': os.path.join(output_dir, 'video.%(ext)s'),
        'merge_output_format': 'mp4',
        'quiet': False,
        'no_warnings': False,
        'retries': 3,
        'socket_timeout': 60,
        'extractor_args': {
            'youtube': {
                'player_client': ['tv_embedded'],
                'skip': ['dash', 'hls'],
            }
        },
        'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}],
    }
    if os.path.exists(COOKIES_PATH):
        ydl_opts['cookiefile'] = COOKIES_PATH
        logger.info(f"yt-dlp: using cookies from {COOKIES_PATH}")

    logger.info("Trying yt-dlp (tv_embedded client)...")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([clean_url])


# ─── Public API ─────────────────────────────────────────────────────────────

def download_youtube_video(url: str, output_dir: str) -> tuple[str, str]:
    """
    Download a YouTube video and extract audio.

    Priority:
      1. Invidious public instances (proxy, no IP block)
      2. cobalt.tools API
      3. yt-dlp with tv_embedded client

    Returns:
        (video_path, audio_path)
    """
    os.makedirs(output_dir, exist_ok=True)
    video_path = os.path.join(output_dir, "video.mp4")
    audio_path = os.path.join(output_dir, "audio.wav")

    for p in [video_path, audio_path]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception as e:
                logger.warning(f"Could not remove {p}: {e}")

    logger.info(f"Downloading: {url}")

    # 1️⃣  Invidious
    if _download_via_invidious(url, video_path):
        pass
    # 2️⃣  cobalt.tools
    elif _download_via_cobalt(url, video_path):
        pass
    # 3️⃣  yt-dlp fallback
    else:
        logger.info("Proxy methods failed — falling back to yt-dlp")
        try:
            _download_via_ytdlp(url, output_dir)
        except Exception as e:
            logger.error(f"yt-dlp failed: {e}")
            raise ValueError(f"Failed to download YouTube video: {e}")

    video_path = _ensure_mp4(output_dir, video_path)

    logger.info("Extracting audio...")
    try:
        _extract_audio(video_path, audio_path)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg audio extraction failed: {e}")

    logger.info("Download complete.")
    return video_path, audio_path
