"""Integration test for DETECTOR=finetuned using a synthetic ONNX detector.

Needs the real InsightFace `buffalo_l` models and the `onnx` package; skipped otherwise.
A tiny ONNX graph returns fixed YOLOv8-format boxes (taken from the pretrained detector), so
the test exercises the real letterbox decode -> NMS -> crop -> landmarks -> ArcFace path.
"""
import os
from pathlib import Path

import numpy as np
import pytest

onnx = pytest.importorskip("onnx")
cv2 = pytest.importorskip("cv2")
insightface = pytest.importorskip("insightface")

MODEL_DIR = Path(os.path.expanduser("~/.insightface/models/buffalo_l"))
pytestmark = pytest.mark.skipif(not MODEL_DIR.exists(), reason="buffalo_l models not downloaded")


def test_finetuned_pipeline_matches_pretrained(tmp_path):
    from onnx import TensorProto, helper, numpy_helper
    from app.services.detector import FinetunedDetector, PretrainedDetector

    sample = Path(insightface.__file__).parent / "data" / "images" / "t1.jpg"
    img = cv2.imread(str(sample))
    H, W = img.shape[:2]
    pre = PretrainedDetector()
    pre.load()
    ref = sorted(pre.detect(img), key=lambda f: f.bbox[0])
    assert len(ref) >= 3

    r = 640 / max(H, W)
    padx, pady = (640 - round(W * r)) / 2, (640 - round(H * r)) / 2
    out = np.zeros((1, 5, 8400), np.float32)
    for i, f in enumerate(ref):
        x1, y1, x2, y2 = f.bbox
        out[0, :, i] = [(x1 + x2) / 2 * r + padx, (y1 + y2) / 2 * r + pady,
                        (x2 - x1) * r, (y2 - y1) * r, 0.9]
    out[0, :, 20] = [300, 300, 50, 50, 0.1]                 # below DET_CONF_MIN
    out[0, :, 21] = out[0, :, 0] + [2, 2, 2, 2, -0.1]       # duplicate -> removed by NMS

    node = helper.make_node("Constant", [], ["output0"], value=numpy_helper.from_array(out))
    graph = helper.make_graph(
        [node], "fake",
        [helper.make_tensor_value_info("images", TensorProto.FLOAT, [1, 3, 640, 640])],
        [helper.make_tensor_value_info("output0", TensorProto.FLOAT, [1, 5, 8400])],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 8
    path = tmp_path / "fake_face.onnx"
    onnx.save(model, str(path))

    ft = FinetunedDetector(model_path=path, pretrained=pre)
    ft.load()
    faces = sorted(ft.detect(img), key=lambda f: f.bbox[0])

    assert ft.version == "finetuned:fake_face.onnx"
    assert len(faces) == len(ref)
    for a, b in zip(ref, faces):
        assert np.abs(np.array(a.bbox) - np.array(b.bbox)).max() < 3          # letterbox undone
        assert b.embedding is not None
        assert float(np.dot(a.embedding, b.embedding)) > 0.85                 # same identity
