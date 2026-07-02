import os
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # AI Models config
    WHISPER_MODEL_NAME: str = "tiny"  # 'tiny', 'base', 'small', 'medium', 'large'
    NLLB_MODEL_NAME: str = "facebook/nllb-200-distilled-600M"

    # Directories
    LOCAL_STORAGE_DIR: str = str(Path(__file__).parent.parent / "static")
    TEMP_DIR: str = str(Path(__file__).parent.parent / "temp")
    # Microsoft Azure Speech
    AZURE_SPEECH_KEY: str = ""
    AZURE_SPEECH_REGION: str = ""

    @property
    def is_azure_configured(self) -> bool:
        return bool(self.AZURE_SPEECH_KEY and self.AZURE_SPEECH_REGION)

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Ensure directories exist
os.makedirs(settings.LOCAL_STORAGE_DIR, exist_ok=True)
os.makedirs(settings.TEMP_DIR, exist_ok=True)

# Programmatic configuration of FFmpeg from imageio-ffmpeg if not in PATH
def configure_ffmpeg():
    import shutil
    import logging
    logger = logging.getLogger("backend.config")
    
    # Check if FFmpeg is already in the system PATH
    if shutil.which("ffmpeg"):
        logger.info("System FFmpeg detected. Using it.")
        return
        
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(ffmpeg_exe):
            bin_dir = Path(__file__).parent / "bin"
            os.makedirs(bin_dir, exist_ok=True)
            local_ffmpeg = bin_dir / "ffmpeg.exe"
            
            # Copy executable if not already copied
            if not os.path.exists(local_ffmpeg):
                logger.info(f"Copying FFmpeg binary from imageio-ffmpeg: {ffmpeg_exe} -> {local_ffmpeg}")
                shutil.copy(ffmpeg_exe, local_ffmpeg)
                
            # Add bin directory to PATH
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ["PATH"]
            logger.info(f"Successfully configured local FFmpeg in PATH: {bin_dir}")
    except Exception as e:
        logger.error(f"Failed to locate and configure local FFmpeg from imageio-ffmpeg: {e}")

configure_ffmpeg()

