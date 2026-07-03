import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.config import settings
from backend.routes.translate import router as translate_router

# Configure logging format and levels
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI YouTube Video Dubber & Translator API",
    description="Modular system translating YouTube videos via speech-to-text, NLLB-200 translation, AWS Polly TTS, and FFmpeg video merging.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(translate_router, prefix="/api", tags=["Translation & Dubbing"])

# Mount static folder for serving downloaded and dubbed assets when running locally
logger.info(f"Mounting static files directory: {settings.LOCAL_STORAGE_DIR}")
app.mount("/static", StaticFiles(directory=settings.LOCAL_STORAGE_DIR), name="static")

# Mount outputs folder for serving dubbed assets
outputs_dir = os.path.abspath("outputs")
os.makedirs(outputs_dir, exist_ok=True)
logger.info(f"Mounting outputs directory: {outputs_dir}")
app.mount("/outputs", StaticFiles(directory=outputs_dir), name="outputs")

@app.get("/health")
def health_check():
    """Basic service health check."""
    return {
        "status": "healthy",
        "service": "AI YouTube Video Dubber & Translator API",
    }

# Serve React frontend (must be LAST - catch-all for SPA routing)
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="frontend-assets")

    @app.get("/")
    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str = ""):
        """Serve React SPA — return index.html for all unmatched routes."""
        index = os.path.join(frontend_dist, "index.html")
        return FileResponse(index)

@app.get("/config")
def get_config():
    """Returns frontend-facing configuration settings."""
    return {
        "is_azure_configured": settings.is_azure_configured,
        "whisper_model": settings.WHISPER_MODEL_NAME,
        "nllb_model": settings.NLLB_MODEL_NAME
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
