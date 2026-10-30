"""Turn an enrollment photo into a face embedding."""
from typing import Optional

import numpy as np

# Enrollment photos are close-ups (selfies). SCRFD has a fixed 640 input; a close-up that fills
# the frame is sometimes only found at 320, so try both.
_DET_SIZES = (640, 320)


def embed_largest_face(insight_app, img_bgr: np.ndarray) -> Optional[np.ndarray]:
    """Return the 512-d ArcFace embedding of the biggest face, or None if no face is found.

    The caller must hold the inference lock (the detector input size is changed temporarily).
    """
    det_model = getattr(insight_app, "det_model", None)
    old_size = getattr(det_model, "input_size", None)
    try:
        faces = []
        for size in _DET_SIZES:
            if det_model is not None:
                det_model.input_size = (size, size)
            faces = insight_app.get(img_bgr)
            if faces:
                break
    finally:
        if det_model is not None and old_size is not None:
            det_model.input_size = old_size

    if not faces:
        return None

    def area(f) -> float:
        x1, y1, x2, y2 = f.bbox
        return float((x2 - x1) * (y2 - y1))

    emb = getattr(max(faces, key=area), "normed_embedding", None)
    return None if emb is None else emb.astype(np.float32)
