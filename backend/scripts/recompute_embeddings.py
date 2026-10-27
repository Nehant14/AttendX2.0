"""
Recompute stored student embeddings using the current model (ArcFace R100).

Run whenever the face recognition/embedding model changes.
Reads all original enrollment photos from disk and updates student_embeddings in DB.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running from project root or backend directory
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

import io
import logging
from sqlalchemy import select
from app.config import settings
from app.db import SessionLocal
from app.models import StudentEmbedding
from app.services.detector import get_detector
from app.services.enrollment import check_enrollment_photo

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("recompute_embeddings")


def recompute():
    logger.info("Initializing detector (%s)...", settings.INSIGHTFACE_MODEL)
    det = get_detector()
    insight_app = det.get_app()
    embedder_ver = getattr(det, "embedder_version", "arcface-r100")

    with SessionLocal() as db:
        rows = db.scalars(select(StudentEmbedding)).all()
        logger.info("Found %d stored embeddings in database.", len(rows))

        updated = 0
        skipped = 0

        for row in rows:
            rel_path = row.source_image_path
            if not rel_path:
                logger.warning("Embedding id=%d has no source_image_path. Skipping.", row.id)
                skipped += 1
                continue

            full_path = Path(rel_path)
            if not full_path.is_file():
                # Try prepending data dir if relative
                full_path = settings.DATA_DIR / rel_path
                if not full_path.is_file():
                    # Try resolving from project root
                    full_path = Path("./data") / rel_path
                    if not full_path.is_file():
                        logger.warning("File not found for embedding id=%d: %s. Skipping.", row.id, rel_path)
                        skipped += 1
                        continue

            try:
                with open(full_path, "rb") as f:
                    img_bytes = f.read()

                res = check_enrollment_photo(
                    img_bytes=img_bytes,
                    filename=full_path.name,
                    insight_app=insight_app,
                )

                if res.accepted and res.embedding is not None:
                    row.embedding = res.embedding.tobytes()
                    row.model_version = embedder_ver
                    row.det_score = res.det_score
                    row.face_px = res.face_px
                    row.blur_var = res.blur_var
                    updated += 1
                    logger.info("Updated embedding id=%d (student_id=%d) with %s", row.id, row.student_id, embedder_ver)
                else:
                    logger.warning("Quality check rejected photo for embedding id=%d: %s", row.id, res.reason)
                    skipped += 1
            except Exception as exc:
                logger.error("Failed processing embedding id=%d (%s): %s", row.id, full_path, exc)
                skipped += 1

        db.commit()
        logger.info("Successfully recomputed and updated %d/%d embeddings. Skipped: %d.", updated, len(rows), skipped)


if __name__ == "__main__":
    recompute()
