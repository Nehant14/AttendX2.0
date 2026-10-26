"""
Threshold calibration script.

Evaluates genuine vs impostor cosine similarities from a folder of images:
  calibration/<student_name>/*.jpg

Computes FAR (False Accept Rate) and GAR (Genuine Accept Rate) at various thresholds,
and outputs recommended SIM_ACCEPT and SIM_REVIEW_MIN values for .env.
"""
from __future__ import annotations

import sys
from pathlib import Path as _P

# Allow `python scripts/<name>.py` from the backend/ folder (the package root is backend/).
sys.path.insert(0, str(_P(__file__).resolve().parent.parent))

import argparse
import itertools
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageOps

from app.services.detector import PretrainedDetector
from app.services.enrollment import detect_faces_multiscale


def load_and_embed(detector, image_path: Path) -> np.ndarray | None:
    try:
        pil = Image.open(image_path)
        pil = ImageOps.exif_transpose(pil).convert("RGB")
        bgr = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
        # Same multi-scale detection as enrollment: calibration photos are close-ups.
        faces = detect_faces_multiscale(detector.get_app(), bgr)
        faces = [f for f in faces if getattr(f, "normed_embedding", None) is not None
                 and (f.bbox[2] - f.bbox[0]) >= 60]
        if not faces:
            return None
        faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
        return faces[0].normed_embedding.astype(np.float32)
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Calibrate face recognition thresholds.")
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path("calibration"),
        help="Path to calibration images folder: calibration/<person>/*.jpg",
    )
    args = parser.parse_args()

    calib_dir: Path = args.dir
    if not calib_dir.exists() or not calib_dir.is_dir():
        print(f"Error: Directory '{calib_dir}' not found.")
        print("Please structure images as: calibration/<person_name>/*.jpg")
        return

    print("Loading pretrained face detector...")
    det = PretrainedDetector()
    det.load()

    # Collect embeddings per person
    person_embeddings: dict[str, list[np.ndarray]] = {}
    subdirs = [p for p in calib_dir.iterdir() if p.is_dir()]
    if not subdirs:
        print(f"No subdirectories found in {calib_dir}.")
        return

    print(f"Found {len(subdirs)} identity directories. Extracting embeddings...")
    for pdir in subdirs:
        person_name = pdir.name
        embs = []
        for img_p in list(pdir.glob("*.jpg")) + list(pdir.glob("*.jpeg")) + list(pdir.glob("*.png")):
            emb = load_and_embed(det, img_p)
            if emb is not None:
                embs.append(emb)
        if embs:
            person_embeddings[person_name] = embs
            print(f"  {person_name}: {len(embs)} valid face photos")
        else:
            print(f"  {person_name}: No valid faces found.")

    if len(person_embeddings) < 2:
        print("Need at least 2 people with valid photos to compute impostor scores.")
        return

    # Compute genuine scores (pairs within same person)
    genuine_scores = []
    for person, embs in person_embeddings.items():
        if len(embs) >= 2:
            for e1, e2 in itertools.combinations(embs, 2):
                genuine_scores.append(float(np.dot(e1, e2)))

    # Compute impostor scores (pairs across different people)
    impostor_scores = []
    people = list(person_embeddings.keys())
    for p1, p2 in itertools.combinations(people, 2):
        for e1 in person_embeddings[p1]:
            for e2 in person_embeddings[p2]:
                impostor_scores.append(float(np.dot(e1, e2)))

    if not genuine_scores or not impostor_scores:
        print("Insufficient pairs to calibrate (need photos of people with >=2 images each).")
        return

    gen_np = np.array(genuine_scores)
    imp_np = np.array(impostor_scores)

    print("\n--- Calibration Results ---")
    print(f"Genuine pairs:  {len(gen_np)} (Mean: {gen_np.mean():.4f}, Std: {gen_np.std():.4f}, Min: {gen_np.min():.4f}, Max: {gen_np.max():.4f})")
    print(f"Impostor pairs: {len(imp_np)} (Mean: {imp_np.mean():.4f}, Std: {imp_np.std():.4f}, Min: {imp_np.min():.4f}, Max: {imp_np.max():.4f})")

    # Threshold for 1% FAR and 0.1% FAR
    imp_sorted = np.sort(imp_np)
    idx_1pct = int(np.ceil((1.0 - 0.01) * len(imp_sorted))) - 1
    idx_01pct = int(np.ceil((1.0 - 0.001) * len(imp_sorted))) - 1

    thr_1pct = imp_sorted[min(max(0, idx_1pct), len(imp_sorted) - 1)]
    thr_01pct = imp_sorted[min(max(0, idx_01pct), len(imp_sorted) - 1)]

    gar_1pct = (gen_np >= thr_1pct).mean() * 100.0
    gar_01pct = (gen_np >= thr_01pct).mean() * 100.0

    print(f"\nFAR 1.0%   Threshold: {thr_1pct:.4f}  | GAR: {gar_1pct:.1f}%")
    print(f"FAR 0.1%   Threshold: {thr_01pct:.4f}  | GAR: {gar_01pct:.1f}%")

    rec_sim_accept = max(0.40, round(float(thr_01pct) + 0.02, 2))
    rec_review_min = max(0.30, round(float(thr_1pct) - 0.02, 2))
    rec_review_min = min(rec_review_min, round(rec_sim_accept - 0.05, 2))   # keep a review band

    print("\n--- Recommended .env Configuration ---")
    print(f"SIM_ACCEPT={rec_sim_accept:.2f}")
    print(f"SIM_REVIEW_MIN={rec_review_min:.2f}")
    print("MARGIN_MIN=0.05")


if __name__ == "__main__":
    main()
