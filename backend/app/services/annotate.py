"""Draw a box (and label) around every detected face."""
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFont

GREEN = (34, 197, 94)
RED = (239, 68, 68)

_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:/Windows/Fonts/arial.ttf",
]


def _font(size: int):
    for p in _FONTS:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def annotate_image(img_bgr, faces: list[dict], max_long_side: int = 3000) -> Image.Image:
    """faces: [{"bbox": [x1,y1,x2,y2], "label": str, "matched": bool}] -> annotated PIL image."""
    h, w = img_bgr.shape[:2]
    scale = min(1.0, max_long_side / max(h, w))
    if scale < 1.0:
        img_bgr = cv2.resize(img_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        w, h = img_bgr.shape[1], img_bgr.shape[0]

    img = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img)
    font = _font(max(12, int(w * 0.016)))
    thickness = max(2, int(w * 0.003))

    for f in faces:
        x1, y1, x2, y2 = [v * scale for v in f["bbox"]]
        color = GREEN if f["matched"] else RED
        draw.rectangle([x1, y1, x2, y2], outline=color, width=thickness)

        l, t, r, b = draw.textbbox((0, 0), f["label"], font=font)
        tw, th = r - l, b - t
        lx = max(0, min(int(x1), w - tw - 6))
        ly = max(0, int(y1) - th - 8)
        draw.rectangle([lx, ly, lx + tw + 6, ly + th + 6], fill=color)
        draw.text((lx + 3, ly + 2), f["label"], font=font, fill=(255, 255, 255))
    return img
