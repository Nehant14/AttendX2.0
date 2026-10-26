"""Main FastAPI application entry point, lifespan management, routers, static serving."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select

from app.config import settings
from app.db import SessionLocal, init_db
from app.errors import register_error_handlers
from app.models import StudentEmbedding, User
from app.routers import attendance, auth, courses, health, sessions, students
from app.security import get_current_user, hash_password
from app.services import enrollment as enroll_svc
from app.services.detector import get_detector
from app.services.storage import is_within

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("attendx")


def seed_admin_user() -> None:
    """Seed admin user if AUTH_ENABLED and no user exists."""
    if not settings.AUTH_ENABLED:
        return
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(func.lower(User.email) == settings.ADMIN_EMAIL.lower()))
        if admin is None:
            logger.info("Seeding initial admin user: %s", settings.ADMIN_EMAIL)
            new_admin = User(
                email=settings.ADMIN_EMAIL,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
            )
            db.add(new_admin)
            db.commit()


def init_roster_cache() -> None:
    """Populate roster cache on startup from DB embeddings."""
    with SessionLocal() as db:
        rows = db.scalars(select(StudentEmbedding)).all()
        items = [
            {
                "student_id": r.student_id,
                "embedding_id": r.id,
                "embedding": np.frombuffer(r.embedding, dtype=np.float32).copy(),
            }
            for r in rows
        ]
        enroll_svc.roster_cache.rebuild(items)
        logger.info("Loaded %d embeddings into roster cache.", len(items))


def check_production_settings() -> None:
    """Refuse to start in prod with insecure defaults."""
    if not settings.is_prod:
        return
    problems = []
    if (settings.SECRET_KEY in ("", "dev-secret-change-me")
            or settings.SECRET_KEY.startswith("change-me")
            or len(settings.SECRET_KEY) < 24):
        problems.append("SECRET_KEY must be a long random string (>= 24 chars)")
    if settings.AUTH_ENABLED and settings.ADMIN_PASSWORD in ("", "nehant123"):
        problems.append("ADMIN_PASSWORD must be changed from the default")
    if problems:
        raise RuntimeError("Insecure configuration for APP_ENV=prod: " + "; ".join(problems))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting AttendX application (env=%s)...", settings.APP_ENV)
    check_production_settings()
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Remove leftovers of interrupted uploads
    import shutil
    shutil.rmtree(settings.DATA_DIR / "tmp", ignore_errors=True)
    init_db()
    seed_admin_user()
    init_roster_cache()

    # Load model (a missing fine-tuned file raises here: the app must fail loudly)
    if settings.SKIP_MODEL_LOAD:
        logger.warning("SKIP_MODEL_LOAD is set: models are NOT loaded.")
        health.set_detector(None, loaded=False)
    else:
        logger.info("Loading detector '%s'...", settings.DETECTOR)
        try:
            det = get_detector()
            health.set_detector(det, loaded=True)
            logger.info("Detector '%s' loaded successfully.", getattr(det, "version", "unknown"))
        except Exception as exc:
            logger.error("Failed to load detector: %s", exc)
            health.set_detector(None, loaded=False)
            raise

    yield

    # Shutdown
    logger.info("Shutting down AttendX application...")


app = FastAPI(
    title="AttendX 2.0 API",
    version="1.0.0",
    lifespan=lifespan,
)

# Exception handlers
register_error_handlers(app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(students.router)
app.include_router(courses.router)
app.include_router(sessions.router)
app.include_router(attendance.router)


# File serving endpoint (login required when auth is enabled)
@app.get("/files/{file_path:path}")
def serve_file(file_path: str, _auth=Depends(get_current_user)):
    parts = Path(file_path).parts
    # Only the image folders are public-by-login. Reject '..' / absolute paths outright and
    # make sure the resolved file stays inside that specific folder (so the SQLite file and
    # anything else in DATA_DIR can never be reached).
    if (
        len(parts) < 2
        or parts[0] not in ("enrollment", "sessions")
        or any(p in ("..", ".", "") or p.startswith("/") for p in parts)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    target = settings.DATA_DIR / file_path
    if not is_within(target, settings.DATA_DIR / parts[0]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return FileResponse(target, headers={"Cache-Control": "private, max-age=3600"})


# Static frontend serving (SPA with catch-all to index.html)
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.is_dir() and (frontend_dist / "index.html").exists():
    if (frontend_dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        # Unknown API / file paths must be JSON 404s, not the SPA page.
        if full_path.startswith(("api/", "files/")) or full_path in ("api", "files"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = frontend_dist / full_path
        if full_path and is_within(candidate, frontend_dist) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(frontend_dist / "index.html", headers={"Cache-Control": "no-cache"})
