"""User settings endpoints — capture/refine and generation defaults."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..services import settings as settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/captures", response_model=models.CaptureSettingsResponse)
async def get_capture_settings_endpoint(db: Session = Depends(get_db)):
    return settings_service.get_capture_settings(db)


@router.put("/captures", response_model=models.CaptureSettingsResponse)
async def update_capture_settings_endpoint(
    patch: models.CaptureSettingsUpdate,
    db: Session = Depends(get_db),
):
    return settings_service.update_capture_settings(db, patch.model_dump(exclude_unset=True))


@router.get("/generation", response_model=models.GenerationSettingsResponse)
async def get_generation_settings_endpoint(db: Session = Depends(get_db)):
    return settings_service.get_generation_settings(db)


@router.put("/generation", response_model=models.GenerationSettingsResponse)
async def update_generation_settings_endpoint(
    patch: models.GenerationSettingsUpdate,
    db: Session = Depends(get_db),
):
    return settings_service.update_generation_settings(db, patch.model_dump(exclude_unset=True))


@router.get("/gpt-sovits/health")
async def get_gpt_sovits_health_endpoint(db: Session = Depends(get_db)):
    """Check the configured local GPT-SoVITS sidecar without generating audio."""
    from ..backends.gpt_sovits_backend import GPTSoVITSBackend

    generation_settings = settings_service.get_generation_settings(db)
    backend = GPTSoVITSBackend(base_url=generation_settings.gpt_sovits_url)
    try:
        await backend.load_model("external")
    except RuntimeError as exc:
        return {
            "connected": False,
            "url": generation_settings.gpt_sovits_url,
            "detail": str(exc),
        }
    return {
        "connected": True,
        "url": generation_settings.gpt_sovits_url,
        "detail": "GPT-SoVITS sidecar is reachable.",
    }
