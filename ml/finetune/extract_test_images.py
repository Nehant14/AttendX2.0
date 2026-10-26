"""
Extract test images with 20-30 faces from WIDER FACE validation split.

Usage:
  python extract_test_images.py \
    --images-dir /path/to/WIDER_val/images \
    --annotations /path/to/wider_face_val_bbx_gt.txt \
    --out test_images \
    --max-images 50
"""
from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path


def parse_wider_val(ann_file: Path) -> list[dict]:
    records = []
    with open(ann_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    idx = 0
    while idx < len(lines):
        rel_img_path = lines[idx]
        idx += 1
        if idx >= len(lines):
            break
        try:
            num_boxes = int(lines[idx])
        except ValueError:
            continue
        idx += 1

        valid_face_count = 0
        if num_boxes == 0:
            if idx < len(lines):
                idx += 1
        else:
            for _ in range(num_boxes):
                if idx < len(lines):
                    parts = [int(v) for v in lines[idx].split()[:10]]
                    invalid = parts[7] if len(parts) > 7 else 0
                    w, h = parts[2], parts[3]
                    if invalid == 0 and w >= 4 and h >= 4:
                        valid_face_count += 1
                    idx += 1

        records.append({"image_rel_path": rel_img_path, "valid_faces": valid_face_count})
    return records


def main():
    parser = argparse.ArgumentParser(description="Extract test images with 20-30 faces.")
    parser.add_argument("--images-dir", type=Path, required=True, help="Directory containing WIDER val images.")
    parser.add_argument("--annotations", type=Path, required=True, help="Path to wider_face_val_bbx_gt.txt.")
    parser.add_argument("--out", type=Path, default=Path("test_images"), help="Output directory.")
    parser.add_argument("--max-images", type=int, default=50, help="Maximum number of images to extract.")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    records = parse_wider_val(args.annotations)

    matching = [r for r in records if 20 <= r["valid_faces"] <= 30]
    print(f"Total images with 20-30 faces in validation split: {len(matching)}")

    selected = matching[: args.max_images]
    manifest_rows = []

    for r in selected:
        rel_path = r["image_rel_path"]
        src = args.images_dir / rel_path
        if not src.exists():
            continue

        # Extract event category from folder name (e.g., '0--Parade/0_Parade_...')
        category = Path(rel_path).parent.name
        dest_filename = f"{category}_{Path(rel_path).name}"
        dest = args.out / dest_filename

        shutil.copy2(src, dest)
        manifest_rows.append({
            "file": dest_filename,
            "face_count": r["valid_faces"],
            "event_category": category,
        })

    manifest_path = args.out / "manifest.csv"
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "face_count", "event_category"])
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"Extracted {len(manifest_rows)} test images to {args.out}")
    print(f"Manifest written to {manifest_path}")


if __name__ == "__main__":
    main()
