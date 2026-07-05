import os
import shutil
import boto3
import logging
from backend.config import settings

logger = logging.getLogger(__name__)

OUTPUT_DIR = "outputs"

def save_file(file_path: str, output_name: str, base_url: str = "") -> str:
    """
    Saves a file. If S3 credentials and bucket name are configured, 
    uploads the file to AWS S3 and returns the public S3 URL.
    Otherwise, saves it locally and returns the local relative URL.
    """
    # 1. Try S3 upload if configured
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY and settings.AWS_S3_BUCKET:
        try:
            logger.info(f"Uploading '{output_name}' to S3 bucket '{settings.AWS_S3_BUCKET}'...")
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_DEFAULT_REGION or "us-east-1"
            )
            
            # Determine ContentType to ensure browser playback rather than forcing download
            content_type = "application/octet-stream"
            if output_name.lower().endswith(".mp4"):
                content_type = "video/mp4"
            elif output_name.lower().endswith(".wav"):
                content_type = "audio/wav"
                
            s3_client.upload_file(
                file_path,
                settings.AWS_S3_BUCKET,
                output_name,
                ExtraArgs={"ContentType": content_type}
            )
            
            region = settings.AWS_DEFAULT_REGION or "us-east-1"
            s3_url = f"https://{settings.AWS_S3_BUCKET}.s3.{region}.amazonaws.com/{output_name}"
            logger.info(f"Successfully uploaded to S3: {s3_url}")
            return s3_url
        except Exception as e:
            logger.error(f"Failed to upload to AWS S3: {e}. Falling back to local storage.")
            
    # 2. Local fallback
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    final_path = os.path.join(OUTPUT_DIR, output_name)
    shutil.copy(file_path, final_path)
    
    cleaned_base = base_url.rstrip("/")
    return f"{cleaned_base}/{OUTPUT_DIR}/{output_name}"
