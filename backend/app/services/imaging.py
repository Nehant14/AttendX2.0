"""Image helpers."""
import io
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps


def decode_image(data: bytes) -> np.ndarray:
    """Bytes -> BGR array, upright (EXIF rotation applied). Raises ValueError if not an image."""
    try:
        pil = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    except Exception as exc:
        raise ValueError("Could not read the file as an image.") from exc
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def save_jpeg(path: Path, img_bgr: np.ndarray, quality: int = 90) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)).save(path, "JPEG", quality=quality)
