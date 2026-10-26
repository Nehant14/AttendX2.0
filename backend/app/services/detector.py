"""
Face detector service.

PretrainedDetector  — wraps InsightFace scrfd_34gf_r100 (SCRFD-34GF detector + ArcFace R100).
FinetunedDetector   — YOLOv8-face for detection; InsightFace for landmarks/embeddings.
get_detector()      — factory called once at startup.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class FaceDetection:
    """Raw output of the detector for one face."""
    bbox: list[float]                   # [x1, y1, x2, y2] in original image coords
    det_score: float
    kps: Optional[np.ndarray]           # (5, 2) or None
    embedding: Optional[np.ndarray]     # 512-d L2-normalised or None
    face_px: int                        # width of bbox in pixels


class PretrainedDetector:
    """Uses InsightFace scrfd_34gf_r100 (SCRFD-34GF detector + ArcFace R100 embedder)."""

    version: str = "scrfd-34gf"
    embedder_version: str = "arcface-r100"

    def __init__(self) -> None:
        self._app = None
        self._lock = threading.Lock()

    def load(self) -> None:
        """Load InsightFace models (auto-downloads scrfd_34gf_r100 on first run)."""
        from insightface.app import FaceAnalysis
        import onnxruntime as ort

        available = ort.get_available_providers()
        providers = [p for p in ["CUDAExecutionProvider", "CPUExecutionProvider"] if p in available]

        logger.info(
            "Loading InsightFace model '%s' (providers=%s)...",
            settings.INSIGHTFACE_MODEL, providers,
        )
        app = FaceAnalysis(
            name=settings.INSIGHTFACE_MODEL,
            root=settings.insightface_home_resolved,
            providers=providers,
            # Only detection (SCRFD-34GF) + recognition (ArcFace R100) are needed; skipping
            # the landmark/gender-age models makes inference noticeably faster.
            allowed_modules=["detection", "recognition"],
        )
        ctx = 0 if "CUDAExecutionProvider" in providers else -1
        # SCRFD-34GF has a fixed 640×640 input baked into the ONNX graph.
        # InsightFace will ignore any det_size override and log a warning; we pass 640
        # explicitly to be consistent and avoid the warning message.
        # det_thresh must follow DET_CONF_MIN, otherwise InsightFace's own 0.5 default wins.
        app.prepare(
            ctx_id=ctx,
            det_thresh=settings.DET_CONF_MIN,
            det_size=(640, 640),
        )
        self._app = app
        logger.info("InsightFace loaded successfully (SCRFD-34GF + ArcFace R100).")

    def detect(self, img_bgr: np.ndarray) -> list[FaceDetection]:
        """Run detection + embedding on a BGR image."""
        if self._app is None:
            raise RuntimeError("Detector not loaded. Call load() first.")
        with self._lock:
            faces = self._app.get(img_bgr)
        results: list[FaceDetection] = []
        for f in faces:
            x1, y1, x2, y2 = f.bbox.tolist()
            face_px = int(x2 - x1)
            kps = f.kps if hasattr(f, "kps") and f.kps is not None else None
            emb = (
                f.normed_embedding.astype(np.float32)
                if hasattr(f, "normed_embedding") and f.normed_embedding is not None
                else None
            )
            results.append(FaceDetection(
                bbox=[float(x1), float(y1), float(x2), float(y2)],
                det_score=float(f.det_score),
                kps=kps,
                embedding=emb,
                face_px=face_px,
            ))
        return results

    @property
    def is_loaded(self) -> bool:
        return self._app is not None

    def get_app(self):
        """Expose the FaceAnalysis app (used by enrollment and FinetunedDetector)."""
        return self._app


class FinetunedDetector:
    """
    YOLOv8-face fine-tuned detector.
    Detection only — landmarks and embeddings come from InsightFace (ArcFace R100) on crops.
    """

    embedder_version: str = "arcface-r100"

    def __init__(self, model_path: Path, pretrained: PretrainedDetector) -> None:
        self._model_path = model_path
        self._pretrained = pretrained
        self._onnx_session = None
        self._yolo_model = None
        self._input_size = 640
        self._lock = threading.Lock()

    @property
    def version(self) -> str:
        return f"finetuned:{self._model_path.name}"

    def load(self) -> None:
        """Load the fine-tuned model (ONNX preferred, .pt fallback)."""
        path = self._model_path
        if not path.exists():
            raise FileNotFoundError(
                f"DETECTOR=finetuned but '{path}' does not exist. "
                "Place face_ft_best.onnx in models/ or set DETECTOR=pretrained."
            )
        if path.suffix == ".onnx":
            import onnxruntime as ort
            available = ort.get_available_providers()
            providers = [p for p in ["CUDAExecutionProvider", "CPUExecutionProvider"] if p in available]
            self._onnx_session = ort.InferenceSession(str(path), providers=providers)
            inp = self._onnx_session.get_inputs()[0]
            if inp.shape and len(inp.shape) == 4 and isinstance(inp.shape[2], int):
                self._input_size = inp.shape[2]
            logger.info("Loaded fine-tuned ONNX from %s (imgsz=%d)", path, self._input_size)
        elif path.suffix == ".pt":
            try:
                from ultralytics import YOLO
                self._yolo_model = YOLO(str(path))
                logger.info("Loaded fine-tuned .pt from %s", path)
            except ImportError:
                raise RuntimeError(
                    "ultralytics is required for .pt models. "
                    "Export to ONNX: yolo export model=face_ft_best.pt format=onnx"
                )
        else:
            raise ValueError(f"Unsupported model format: {path.suffix}. Use .onnx or .pt.")

    @property
    def is_loaded(self) -> bool:
        return (
            self._onnx_session is not None or self._yolo_model is not None
        ) and self._pretrained.is_loaded

    def get_app(self):
        """Enrollment always uses the pretrained InsightFace pipeline."""
        return self._pretrained.get_app()

    def _crop_faces(self, crop: np.ndarray):
        """Run InsightFace on a small crop using a small detector input size (spec 8.5)."""
        app = self._pretrained.get_app()
        det_model = app.det_model
        old_size = det_model.input_size
        try:
            det_model.input_size = (320, 320)
            with self._pretrained._lock:
                return app.get(crop)
        finally:
            det_model.input_size = old_size

    def detect(self, img_bgr: np.ndarray) -> list[FaceDetection]:
        """Run fine-tuned detection then InsightFace on each crop for embedding."""
        raw_boxes = self._run_detector(img_bgr)
        h, w = img_bgr.shape[:2]
        results: list[FaceDetection] = []

        for x1, y1, x2, y2, score in raw_boxes:
            face_px = int(x2 - x1)
            bw, bh = x2 - x1, y2 - y1
            mx, my = bw * 0.25, bh * 0.25
            cx1 = max(0, int(x1 - mx))
            cy1 = max(0, int(y1 - my))
            cx2 = min(w, int(x2 + mx))
            cy2 = min(h, int(y2 + my))
            crop = img_bgr[cy1:cy2, cx1:cx2]

            ch, cw = crop.shape[:2]
            if min(ch, cw) < 1:
                results.append(FaceDetection(
                    bbox=[x1, y1, x2, y2], det_score=score,
                    kps=None, embedding=None, face_px=face_px,
                ))
                continue

            scale = 160 / min(ch, cw)
            if scale > 1.0:
                crop = cv2.resize(crop, (int(cw * scale), int(ch * scale)))

            try:
                app = self._pretrained.get_app()
                if app is not None:
                    crop_faces = self._crop_faces(crop)
                    if crop_faces:
                        best = self._pick_best(crop_faces, crop.shape)
                        kps = None
                        if hasattr(best, "kps") and best.kps is not None:
                            kps = best.kps.copy()
                            kps[:, 0] = kps[:, 0] / (scale if scale > 1 else 1) + cx1
                            kps[:, 1] = kps[:, 1] / (scale if scale > 1 else 1) + cy1
                        emb = (
                            best.normed_embedding.astype(np.float32)
                            if hasattr(best, "normed_embedding") and best.normed_embedding is not None
                            else None
                        )
                        results.append(FaceDetection(
                            bbox=[x1, y1, x2, y2], det_score=score,
                            kps=kps, embedding=emb, face_px=face_px,
                        ))
                    else:
                        results.append(FaceDetection(
                            bbox=[x1, y1, x2, y2], det_score=score,
                            kps=None, embedding=None, face_px=face_px,
                        ))
                else:
                    results.append(FaceDetection(
                        bbox=[x1, y1, x2, y2], det_score=score,
                        kps=None, embedding=None, face_px=face_px,
                    ))
            except Exception as exc:
                logger.warning("Crop failed for [%s]: %s", [x1, y1, x2, y2], exc)
                results.append(FaceDetection(
                    bbox=[x1, y1, x2, y2], det_score=score,
                    kps=None, embedding=None, face_px=face_px,
                ))
        return results

    # ── internal helpers ──────────────────────────────────────────────────────

    def _pick_best(self, faces, crop_shape):
        h, w = crop_shape[:2]
        cx, cy = w / 2, h / 2
        best, best_d = faces[0], float("inf")
        for f in faces:
            bx1, by1, bx2, by2 = f.bbox
            d = ((bx1 + bx2) / 2 - cx) ** 2 + ((by1 + by2) / 2 - cy) ** 2
            if d < best_d:
                best, best_d = f, d
        return best

    def _run_detector(self, img_bgr: np.ndarray) -> list[tuple]:
        if self._yolo_model is not None:
            return self._run_pt(img_bgr)
        return self._run_onnx(img_bgr)

    def _run_pt(self, img_bgr: np.ndarray) -> list[tuple]:
        results = self._yolo_model(img_bgr, conf=settings.DET_CONF_MIN, iou=0.5, verbose=False)
        boxes = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                boxes.append((x1, y1, x2, y2, float(box.conf[0])))
        return boxes

    def _run_onnx(self, img_bgr: np.ndarray) -> list[tuple]:
        """Letterbox to the export size (as Ultralytics does), run, decode, undo letterbox."""
        h, w = img_bgr.shape[:2]
        sz = self._input_size
        r = min(sz / h, sz / w)
        new_w, new_h = int(round(w * r)), int(round(h * r))
        resized = cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        pad_x, pad_y = (sz - new_w) / 2.0, (sz - new_h) / 2.0
        canvas = np.full((sz, sz, 3), 114, dtype=np.uint8)
        left, top = int(round(pad_x - 0.1)), int(round(pad_y - 0.1))
        canvas[top:top + new_h, left:left + new_w] = resized
        img_f = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        inp = np.transpose(img_f, (2, 0, 1))[np.newaxis]
        name = self._onnx_session.get_inputs()[0].name
        with self._lock:
            preds = self._onnx_session.run(None, {name: inp})[0]
        # YOLOv8 output: (1, 4+nc[+kpts], anchors) -> (anchors, 4+nc[+kpts])
        preds = preds[0]
        if preds.shape[0] < preds.shape[1]:
            preds = preds.T
        return self._decode(preds, w, h, r, left, top)

    def _decode(
        self, preds: np.ndarray, orig_w: int, orig_h: int, ratio: float, pad_x: int, pad_y: int
    ) -> list[tuple]:
        mask = preds[:, 4] >= settings.DET_CONF_MIN
        preds = preds[mask]
        if len(preds) == 0:
            return []
        cx, cy, bw, bh, conf = preds[:, 0], preds[:, 1], preds[:, 2], preds[:, 3], preds[:, 4]
        x1 = np.clip((cx - bw / 2 - pad_x) / ratio, 0, orig_w)
        y1 = np.clip((cy - bh / 2 - pad_y) / ratio, 0, orig_h)
        x2 = np.clip((cx + bw / 2 - pad_x) / ratio, 0, orig_w)
        y2 = np.clip((cy + bh / 2 - pad_y) / ratio, 0, orig_h)
        boxes = np.stack([x1, y1, x2, y2], axis=1)
        keep = self._nms(boxes, conf, 0.5)
        return [(float(x1[i]), float(y1[i]), float(x2[i]), float(y2[i]), float(conf[i])) for i in keep]

    @staticmethod
    def _nms(boxes: np.ndarray, scores: np.ndarray, iou_thr: float) -> list[int]:
        order = scores.argsort()[::-1]
        keep: list[int] = []
        while len(order):
            i = order[0]
            keep.append(int(i))
            if len(order) == 1:
                break
            xx1 = np.maximum(boxes[i, 0], boxes[order[1:], 0])
            yy1 = np.maximum(boxes[i, 1], boxes[order[1:], 1])
            xx2 = np.minimum(boxes[i, 2], boxes[order[1:], 2])
            yy2 = np.minimum(boxes[i, 3], boxes[order[1:], 3])
            inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
            a_i = (boxes[i, 2] - boxes[i, 0]) * (boxes[i, 3] - boxes[i, 1])
            areas = (boxes[order[1:], 2] - boxes[order[1:], 0]) * (boxes[order[1:], 3] - boxes[order[1:], 1])
            iou = inter / (a_i + areas - inter + 1e-6)
            order = order[1:][iou < iou_thr]
        return keep


def get_detector() -> PretrainedDetector | FinetunedDetector:
    """Factory: build and load the configured detector."""
    pretrained = PretrainedDetector()
    pretrained.load()

    if settings.DETECTOR == "finetuned":
        path = settings.FINETUNED_MODEL_PATH
        if not path.exists():
            raise FileNotFoundError(
                f"DETECTOR=finetuned but model not found at '{path}'. "
                "Place face_ft_best.onnx in models/ or set DETECTOR=pretrained."
            )
        ft = FinetunedDetector(model_path=path, pretrained=pretrained)
        ft.load()
        return ft

    return pretrained
