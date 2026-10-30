"""Class photo -> which students are in it, plus the annotated photo."""
import numpy as np
from PIL import Image

from app.config import settings
from app.services.annotate import annotate_image
from app.services.matcher import match_faces


def run_pipeline(
    img_bgr: np.ndarray,
    detector,
    names: list[str],            # K student names (column order)
    roster_embs: np.ndarray,     # (M, 512)
    owner_cols: np.ndarray,      # (M,) student column of each enrolled photo
) -> tuple[dict[int, float], Image.Image]:
    """Returns ({student_column: similarity} for every recognised student, annotated image)."""
    faces = detector.detect(img_bgr)                                  # 1. find every face

    with_emb = [i for i, f in enumerate(faces) if f.embedding is not None]
    matches = {}                                                      # 2. who is it?
    labels = {}
    if with_emb:
        result = match_faces(
            np.stack([faces[i].embedding for i in with_emb]),
            roster_embs, owner_cols, len(names), settings.SIM_THRESHOLD,
        )
        for i, (col, sim) in zip(with_emb, result):
            if col is not None:
                matches[col] = sim
                labels[i] = (f"{names[col]} {sim * 100:.0f}%", True)

    annotated = annotate_image(                                       # 3. draw the boxes
        img_bgr,
        [{"bbox": f.bbox, "label": labels.get(i, ("Unknown", False))[0],
          "matched": labels.get(i, ("", False))[1]} for i, f in enumerate(faces)],
    )
    return matches, annotated
