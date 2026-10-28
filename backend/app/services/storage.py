"""File storage helpers: paths, safe save, deletion."""
from __future__ import annotations

import io
import shutil
import uuid
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from app.config import settings


def enrollment_dir(student_id: int) -> Path:
    """Return (and create) the enrollment photo directory for a student."""
    p = settings.DATA_DIR / "enrollment" / str(student_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def session_dir(session_id: int) -> Path:
    """Return (and create) the session image directory."""
    p = settings.DATA_DIR / "sessions" / str(session_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_image_bytes(directory: Path, image_bytes: bytes, suffix: str = "") -> Path:
    """Decode image bytes, EXIF-rotate, re-encode as JPEG under a UUID name."""
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    name = f"{uuid.uuid4().hex}{suffix}.jpg"
    dest = directory / name
    img.save(dest, "JPEG", quality=90)
    return dest


def save_named_image(directory: Path, image: Image.Image, name: str) -> Path:
    """Save a PIL Image as JPEG at directory/name."""
    dest = directory / name
    image.convert("RGB").save(dest, "JPEG", quality=90)
    return dest


def save_bgr_as_jpeg(directory: Path, img_bgr: np.ndarray, name: str) -> Path:
    """Save an OpenCV BGR array as JPEG."""
    from PIL import Image as _PIL
    import cv2 as _cv2
    rgb = _cv2.cvtColor(img_bgr, _cv2.COLOR_BGR2RGB)
    pil = _PIL.fromarray(rgb)
    return save_named_image(directory, pil, name)


def relative_to_data(path: Path | str) -> str:
    """Return a POSIX path relative to DATA_DIR (for DB storage and /files URLs).

    Already-relative paths are returned unchanged, so this is idempotent.
    """
    # Rows written on Windows may hold backslashes; read them correctly on any OS.
    if isinstance(path, str) and "\\" in path:
        path = path.replace("\\", "/")
    p = Path(path)
    parts = p.parts
    if parts and parts[0] in ("enrollment", "sessions"):
        return p.as_posix()
    if parts and parts[0] == "data" and len(parts) > 1 and parts[1] in ("enrollment", "sessions"):
        return Path(*parts[1:]).as_posix()
    try:
        return p.resolve().relative_to(settings.DATA_DIR.resolve()).as_posix()
    except ValueError:
        if parts and "data" in parts:
            idx = parts.index("data")
            if idx + 1 < len(parts) and parts[idx + 1] in ("enrollment", "sessions"):
                return Path(*parts[idx + 1:]).as_posix()
        return p.as_posix()


def absolute_from_data(path: Path | str) -> Path:
    """Resolve a stored (relative or legacy absolute) path to an absolute filesystem path."""
    if isinstance(path, str) and "\\" in path:
        path = path.replace("\\", "/")
    p = Path(path)
    return p if p.is_absolute() else (settings.DATA_DIR / p)


def is_within(child: Path, parent: Path) -> bool:
    """True if ``child`` is inside ``parent`` (after resolving symlinks / '..')."""
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def data_url(rel_path: str) -> str:
    """Convert a relative data path to a /files/ URL."""
    rel_path = rel_path.replace("\\", "/")
    p = Path(rel_path)
    parts = p.parts
    if parts and parts[0] == "data" and len(parts) > 1 and parts[1] in ("enrollment", "sessions"):
        rel_path = Path(*parts[1:]).as_posix()
    return f"/files/{rel_path}"


def delete_file(path: Path | str | None) -> None:
    """Delete a file if it exists; silently ignore missing."""
    if path is None:
        return
    p = Path(path)
    if p.exists() and p.is_file():
        p.unlink()


def delete_directory(path: Path | str | None) -> None:
    """Recursively delete a directory if it exists."""
    if path is None:
        return
    p = Path(path)
    if p.exists() and p.is_dir():
        shutil.rmtree(p)
