import os
import subprocess
import logging

logger = logging.getLogger(__name__)

def merge_audio_and_video(video_path: str, audio_path: str, output_path: str) -> str:
    """
    Merges the video stream from video_path and the audio stream from audio_path.
    The video stream is copied without re-encoding to maximize speed and maintain quality.
    
    Args:
        video_path (str): Path to the source MP4 video.
        audio_path (str): Path to the synchronized WAV audio.
        output_path (str): Path to save the final dubbed MP4 video.
        
    Returns:
        str: Path to the generated dubbed video.
    """
    logger.info(f"Merging video {video_path} and audio {audio_path} into {output_path}...")
    
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
    # FFmpeg command:
    # -c:v copy: Copies the video stream without re-encoding
    # -c:a aac: Re-encodes the WAV audio to standard AAC format compatible with MP4
    # -map 0:v:0: Maps the video from the first input
    # -map 1:a:0: Maps the audio from the second input
    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-i', audio_path,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-map', '0:v:0',
        '-map', '1:a:0',
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg video/audio merge failed: {e}")
        raise RuntimeError(f"Failed to merge dubbed audio with video stream: {e}")
        
    logger.info(f"Dubbed video successfully merged and saved to {output_path}")
    return output_path
