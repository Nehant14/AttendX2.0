"""Turn an enrollment photo into face embeddings: the photo itself + a few low-resolution copies."""
from typing import Optional

import cv2
import numpy as np

# Enrollment photos are close-ups (selfies). SCRFD has a fixed 640 input; a close-up that fills
# the frame is sometimes only found at 320, so try both.
_DET_SIZES = (640, 320)

# Faces at the back of a class photo are only ~20-60 px wide, so besides the sharp embedding we also
# store embeddings of the same photo shrunk to these face widths and scaled back up. Tested with
# ArcFace: other people's faces stay below ~0.25 similarity even at 16 px (match threshold is 0.45).
DEGRADE_FACE_PX = (64, 40, 24)

# A degraded copy must still look like its own sharp photo, otherwise it is junk and is dropped.
MIN_SELF_SIM = 0.6


def _largest_face(insight_app, img_bgr: np.ndarray):
    """Biggest face (with an embedding) in the photo, or None. Caller must hold the inference lock."""
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

    faces = [f for f in faces if getattr(f, "normed_embedding", None) is not None]
    if not faces:
        return None
    return max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))


def embed_photo(insight_app, img_bgr: np.ndarray) -> Optional[np.ndarray]:
    """Return a (k, 512) float32 array - row 0 is the photo, the other rows are low-res copies.

    Returns None if no face is found.
    """
    face = _largest_face(insight_app, img_bgr)
    if face is None:
        return None

    sharp = face.normed_embedding.astype(np.float32)
    rows = [sharp]
    face_w = float(face.bbox[2] - face.bbox[0])
    h, w = img_bgr.shape[:2]

    for px in DEGRADE_FACE_PX:
        if px >= face_w:
            continue  # the photo's face is already that small
        f = px / face_w
        small = cv2.resize(img_bgr, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        blurry = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
        d = _largest_face(insight_app, blurry)
        if d is not None and float(d.normed_embedding @ sharp) >= MIN_SELF_SIM:
            rows.append(d.normed_embedding.astype(np.float32))

    return np.stack(rows)
