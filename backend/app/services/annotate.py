"""
Annotation service: draw colour-coded bounding boxes and labels on attendance photos.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# RGB colours per label
_COLOURS: dict[str, tuple[int, int, int]] = {
    "recognized":    (34, 197, 94),    # green
    "review":        (234, 179, 8),    # yellow
    "unknown":       (239, 68, 68),    # red
    "unrecognizable":(156, 163, 175),  # gray
}

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for p in _FONT_CANDIDATES:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def build_detection_dicts(
    raw_detections: list[dict],
    student_idx_to_name: dict[int, str],
) -> list[dict]:
    """
    Convert raw detection records into annotation dicts.

    Each raw detection must have:
        bbox, label, student_index (optional), similarity (optional), det_score
    """
    out = []
    for det in raw_detections:
        label = det.get("label", "unknown")
        sim = det.get("similarity")
        sidx = det.get("student_index")
        name = student_idx_to_name.get(sidx, "Unknown") if sidx is not None else "Unknown"

        if label == "recognized" and sim is not None:
            display = f"{name} ({sim:.2f})"
        elif label == "review" and sim is not None:
            display = f"{name}? ({sim:.2f})"
        elif label == "unknown":
            display = "Unknown"
        else:
            display = "Too small"

        out.append({
            "bbox": det["bbox"],
            "label": label,
            "display_name": display,
            "det_score": det.get("det_score", 0.0),
        })
    return out


def annotate_image(
    img_bgr: np.ndarray,
    detections: list[dict],
    max_long_side: int = 3000,
) -> Image.Image:
    """
    Draw annotated bounding boxes on the image.

    Args:
        img_bgr: OpenCV BGR numpy array.
        detections: List of dicts with bbox, label, display_name, det_score.
        max_long_side: Downscale if image is larger than this.

    Returns:
        PIL Image (RGB) with annotations.
    """
    h, w = img_bgr.shape[:2]
    scale = 1.0
    if max(h, w) > max_long_side:
        scale = max_long_side / max(h, w)
        img_bgr = cv2.resize(img_bgr, (int(w * scale), int(h * scale)),
                             interpolation=cv2.INTER_AREA)
        h, w = img_bgr.shape[:2]

    pil_img = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    font_size = max(12, int(w * 0.018))
    font = _get_font(font_size)
    thickness = max(2, int(w * 0.003))

    for det in detections:
        x1, y1, x2, y2 = [v * scale for v in det["bbox"]]
        label = det.get("label", "unknown")
        display = det.get("display_name", "Unknown")
        color = _COLOURS.get(label, (128, 128, 128))

        draw.rectangle([x1, y1, x2, y2], outline=color, width=thickness)

        try:
            tb = draw.textbbox((0, 0), display, font=font)
            tw, th = tb[2] - tb[0], tb[3] - tb[1]
        except Exception:
            tw, th = font_size * len(display) // 2, font_size

        lx = max(0, min(int(x1), w - tw - 4))
        ly = max(0, int(y1) - th - 6)

        draw.rectangle([lx, ly, lx + tw + 4, ly + th + 4], fill=color)
        brightness = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
        text_col = (0, 0, 0) if brightness > 128 else (255, 255, 255)
        draw.text((lx + 2, ly + 2), display, font=font, fill=text_col)

    return pil_img
