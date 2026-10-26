"""
Convert WIDER FACE annotations to YOLO format.

Usage:
  python convert_wider_to_yolo.py \
    --images-dir /path/to/WIDER_train/images \
    --annotations /path/to/wider_face_train_bbx_gt.txt \
    --split train \
    --limit 3000 \
    --seed 42 \
    --out datasets/widerface
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
from pathlib import Path
from PIL import Image, ImageDraw


def parse_wider_annotations(ann_file: Path) -> list[dict]:
    """Parse wider_face_*_bbx_gt.txt format."""
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
            # Handle potential blank lines or corrupted headers
            continue
        idx += 1

        boxes = []
        if num_boxes == 0:
            # Dummy line of zeros
            if idx < len(lines):
                idx += 1
        else:
            for _ in range(num_boxes):
                if idx < len(lines):
                    parts = [int(v) for v in lines[idx].split()[:10]]
                    boxes.append(parts)
                    idx += 1

        records.append({"image_rel_path": rel_img_path, "boxes": boxes})
    return records


def main():
    parser = argparse.ArgumentParser(description="Convert WIDER FACE annotations to YOLO format.")
    parser.add_argument("--images-dir", type=Path, required=True, help="Directory containing WIDER images.")
    parser.add_argument("--annotations", type=Path, required=True, help="Path to wider_face_*_bbx_gt.txt.")
    parser.add_argument("--split", choices=["train", "val"], required=True, help="Split name.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of images (for training subset).")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible subsampling.")
    parser.add_argument("--out", type=Path, default=Path("datasets/widerface"), help="Output directory.")
    args = parser.parse_args()

    out_images_dir = args.out / "images" / args.split
    out_labels_dir = args.out / "labels" / args.split
    check_dir = args.out / "check"

    out_images_dir.mkdir(parents=True, exist_ok=True)
    out_labels_dir.mkdir(parents=True, exist_ok=True)
    check_dir.mkdir(parents=True, exist_ok=True)

    print(f"Parsing annotations from {args.annotations}...")
    records = parse_wider_annotations(args.annotations)
    print(f"Total images in annotation file: {len(records)}")

    # Reproducible shuffle when a limit is set. We stop once `limit` images have actually
    # been written (images without valid faces are skipped for training and must not
    # count against the limit).
    if args.limit and args.limit < len(records):
        random.Random(args.seed).shuffle(records)
        print(f"Shuffled with seed {args.seed}; will write up to {args.limit} images.")

    total_images_processed = 0
    total_faces_written = 0
    total_boxes_skipped = 0
    check_samples = []

    for item in records:
        if args.limit and total_images_processed >= args.limit:
            break
        rel_path = item["image_rel_path"]
        img_src = args.images_dir / rel_path
        if not img_src.exists():
            continue

        try:
            with Image.open(img_src) as img:
                w_img, h_img = img.size
        except Exception as e:
            print(f"Failed to open image {img_src}: {e}")
            continue

        yolo_lines = []
        raw_boxes_for_check = []
        for b in item["boxes"]:
            # Format: x y w h blur expression illumination invalid occlusion pose
            x, y, w, h = b[0], b[1], b[2], b[3]
            invalid = b[7] if len(b) > 7 else 0

            if invalid != 0 or w < 4 or h < 4:
                total_boxes_skipped += 1
                continue

            cx = min(max((x + w / 2.0) / w_img, 0.0), 1.0)
            cy = min(max((y + h / 2.0) / h_img, 0.0), 1.0)
            nw = min(max(float(w) / w_img, 0.0), 1.0)
            nh = min(max(float(h) / h_img, 0.0), 1.0)

            yolo_lines.append(f"0 {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
            raw_boxes_for_check.append((x, y, x + w, y + h))
            total_faces_written += 1

        # Skip training images with no valid faces
        if args.split == "train" and len(yolo_lines) == 0:
            continue

        # Target filenames
        flat_name = rel_path.replace("/", "_")
        stem = Path(flat_name).stem
        dest_img = out_images_dir / f"{stem}.jpg"
        dest_txt = out_labels_dir / f"{stem}.txt"

        # Copy image
        shutil.copy2(img_src, dest_img)

        # Write YOLO label
        with open(dest_txt, "w", encoding="utf-8") as f:
            f.write("\n".join(yolo_lines) + "\n")

        total_images_processed += 1

        if len(check_samples) < 10 and len(raw_boxes_for_check) > 0:
            check_samples.append((img_src, raw_boxes_for_check, stem))

    # Generate visual check images
    print("Generating check sample images...")
    for src_p, bboxes, stem in check_samples:
        try:
            with Image.open(src_p) as img:
                draw = ImageDraw.Draw(img)
                for box in bboxes:
                    draw.rectangle(box, outline="red", width=2)
                img.save(check_dir / f"check_{stem}.jpg")
        except Exception:
            pass

    report = {
        "split": args.split,
        "images_processed": total_images_processed,
        "faces_written": total_faces_written,
        "boxes_skipped": total_boxes_skipped,
    }
    with open(args.out / f"conversion_report_{args.split}.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n--- Conversion Report ---")
    print(json.dumps(report, indent=2))
    print(f"Output saved to {args.out}")


if __name__ == "__main__":
    main()
