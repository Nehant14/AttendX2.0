"""Health check endpoint."""
from fastapi import APIRouter
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Student, StudentEmbedding
from app.schemas import HealthOut

router = APIRouter(prefix="/api", tags=["health"])

# Populated by main.py lifespan
_detector_ref: list = []
_models_loaded: list[bool] = [False]


def set_detector(det, loaded: bool) -> None:
    _detector_ref.clear()
    _detector_ref.append(det)
    _models_loaded[0] = loaded


@router.get("/health", response_model=HealthOut)
def health():
    det = _detector_ref[0] if _detector_ref else None
    det_ver = getattr(det, "version", "not loaded")
    emb_ver = getattr(det, "embedder_version", "not loaded")

    with SessionLocal() as db:
        n_students = db.scalar(select(func.count()).select_from(Student)) or 0
        n_embs = db.scalar(select(func.count()).select_from(StudentEmbedding)) or 0

    return HealthOut(
        status="ok",
        detector=det_ver,
        embedder=emb_ver,
        models_loaded=_models_loaded[0],
        students=n_students,
        embeddings=n_embs,
    )
