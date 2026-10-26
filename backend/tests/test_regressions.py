"""Regression tests for bugs found during the project review."""
import io
import os
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from app.config import settings
from app.routers import health
from app.security import create_access_token
from app.services.detector import FaceDetection, FinetunedDetector
from app.services.pipeline import decode_image
from tests.conftest import create_test_image_bytes, make_unit_vector


@pytest.fixture
def auth():
    return {"Authorization": f"Bearer {create_access_token(1, 'a@b.c', 'admin')}"}


def _mock_detector(face_embeddings=()):
    det = MagicMock()
    det.is_loaded = True
    det.version = "scrfd-buffalo_l"
    det.embedder_version = "arcface-buffalo_l"
    det.detect.return_value = [
        FaceDetection(bbox=[50.0, 50.0, 150.0, 150.0], det_score=0.95, kps=None,
                      embedding=e, face_px=100) for e in face_embeddings
    ]
    return det


def _enroll(client, auth, roll, name, emb, det):
    """Create a student and give them one embedding via the (mocked) enrollment path."""
    sid = client.post("/api/students", json={"roll_no": roll, "full_name": name}, headers=auth).json()["id"]
    app_mock = MagicMock()
    face = MagicMock()
    face.det_score, face.bbox, face.normed_embedding = 0.9, np.array([10, 10, 190, 190], np.float32), emb
    app_mock.get.return_value = [face]
    det.get_app.return_value = app_mock
    with patch("app.services.enrollment.compute_blur_variance", return_value=100.0):
        r = client.post(f"/api/students/{sid}/photos", headers=auth,
                        files=[("files", ("a.jpg", create_test_image_bytes(), "image/jpeg"))])
    assert r.status_code == 200 and r.json()["results"][0]["accepted"], r.text
    return sid


def _course(client, auth, sids, code="C1"):
    cid = client.post("/api/courses", json={"code": code, "name": "Course"}, headers=auth).json()["id"]
    r = client.put(f"/api/courses/{cid}/students", json={"student_ids": sids}, headers=auth)
    return cid, r


def _post_session(client, auth, cid, data=None, content=None, name="p.jpg", ctype="image/jpeg"):
    form = {"course_id": cid, "session_date": "2026-10-21", "period": 1, **(data or {})}
    return client.post("/api/sessions", data=form, headers=auth,
                       files={"file": (name, content or create_test_image_bytes(300, 300), ctype)})


class TestErrorFormat:
    def test_missing_token_has_code(self, client):
        r = client.get("/api/students")
        assert r.status_code == 401 and r.json()["code"] == "UNAUTHORIZED"

    def test_bad_login_has_code(self, client):
        r = client.post("/api/auth/login", json={"email": "x@y.z", "password": "nope"})
        assert r.status_code == 401 and r.json()["code"] == "UNAUTHORIZED"

    def test_validation_error_shape(self, client, auth):
        r = client.post("/api/students", json={"roll_no": "  ", "full_name": "A"}, headers=auth)
        assert r.status_code == 422 and r.json()["code"] == "VALIDATION_ERROR"
        assert isinstance(r.json()["detail"], str)

    def test_unknown_course_404(self, client, auth):
        assert client.get("/api/courses/999", headers=auth).json()["code"] == "NOT_FOUND"


class TestRoster:
    def test_put_roster_returns_students(self, client, auth):
        s1 = client.post("/api/students", json={"roll_no": "1", "full_name": "A"}, headers=auth).json()["id"]
        s2 = client.post("/api/students", json={"roll_no": "2", "full_name": "B"}, headers=auth).json()["id"]
        cid, r = _course(client, auth, [s1, s2])
        body = r.json()
        assert body["student_count"] == 2 and [s["roll_no"] for s in body["students"]] == ["1", "2"]
        # replace with a smaller roster
        r = client.put(f"/api/courses/{cid}/students", json={"student_ids": [s2]}, headers=auth)
        assert r.json()["student_count"] == 1
        assert client.get("/api/courses", headers=auth).json()[0]["student_count"] == 1

    def test_unknown_student_id_rejected(self, client, auth):
        cid, _ = _course(client, auth, [])
        r = client.put(f"/api/courses/{cid}/students", json={"student_ids": [42]}, headers=auth)
        assert r.status_code == 422


class TestStudentPatch:
    def test_can_clear_email_but_not_name(self, client, auth):
        sid = client.post("/api/students", json={"roll_no": "9", "full_name": "N", "email": "a@b.c"},
                          headers=auth).json()["id"]
        r = client.patch(f"/api/students/{sid}", json={"email": None, "full_name": None}, headers=auth)
        assert r.status_code == 200 and r.json()["email"] is None and r.json()["full_name"] == "N"


class TestSessions:
    def test_unsupported_and_oversized(self, client, auth):
        det = _mock_detector([make_unit_vector(seed=1)])
        health.set_detector(det, loaded=True)
        sid = _enroll(client, auth, "1", "A", make_unit_vector(seed=1), det)
        cid, _ = _course(client, auth, [sid])
        r = _post_session(client, auth, cid, content=b"not an image", name="x.txt", ctype="text/plain")
        assert r.status_code == 415 and r.json()["code"] == "UNSUPPORTED_MEDIA"
        with patch.object(settings, "MAX_UPLOAD_MB", 1):
            r = _post_session(client, auth, cid, content=b"\0" * (2 * 1024 * 1024))
        assert r.status_code == 413 and r.json()["code"] == "FILE_TOO_LARGE"

    def test_no_embeddings_422(self, client, auth):
        health.set_detector(_mock_detector(), loaded=True)
        sid = client.post("/api/students", json={"roll_no": "1", "full_name": "A"}, headers=auth).json()["id"]
        cid, _ = _course(client, auth, [sid])
        r = _post_session(client, auth, cid)
        assert r.status_code == 422 and r.json()["code"] == "NO_ENROLLED_EMBEDDINGS"

    def test_failed_replace_keeps_old_session(self, client, auth):
        e = make_unit_vector(seed=3)
        det = _mock_detector([e])
        health.set_detector(det, loaded=True)
        sid = _enroll(client, auth, "1", "A", e, det)
        cid, _ = _course(client, auth, [sid])
        first = _post_session(client, auth, cid)
        assert first.status_code == 201, first.text
        old_id = first.json()["id"]
        bad = _post_session(client, auth, cid, {"replace": True}, content=b"garbage", name="g.jpg")
        assert bad.status_code == 415
        again = client.get(f"/api/sessions/{old_id}", headers=auth)
        assert again.status_code == 200
        img = client.get(again.json()["annotated_url"], headers=auth)
        assert img.status_code == 200 and img.headers["content-type"] == "image/jpeg"

    def test_replace_works_and_leaves_one_session(self, client, auth):
        e = make_unit_vector(seed=3)
        det = _mock_detector([e])
        health.set_detector(det, loaded=True)
        sid = _enroll(client, auth, "1", "A", e, det)
        cid, _ = _course(client, auth, [sid])
        assert _post_session(client, auth, cid).status_code == 201
        r = _post_session(client, auth, cid, {"replace": True})
        assert r.status_code == 201
        assert len(client.get("/api/sessions", headers=auth).json()) == 1
        assert client.get(r.json()["annotated_url"], headers=auth).status_code == 200

    def test_student_without_photos_is_absent_not_missing(self, client, auth):
        e = make_unit_vector(seed=5)
        det = _mock_detector([e])
        health.set_detector(det, loaded=True)
        s1 = _enroll(client, auth, "1", "Has Photos", e, det)
        s2 = client.post("/api/students", json={"roll_no": "2", "full_name": "No Photos"},
                         headers=auth).json()["id"]
        cid, _ = _course(client, auth, [s1, s2])
        body = _post_session(client, auth, cid).json()
        by_roll = {r["roll_no"]: r["status"] for r in body["records"]}
        assert by_roll == {"1": "present", "2": "absent"}
        assert body["counts"]["enrolled"] == 2

    def test_session_survives_missing_user_row(self, client, auth):
        """Token for a user id that doesn't exist must not break session creation (FK)."""
        e = make_unit_vector(seed=6)
        det = _mock_detector([e])
        health.set_detector(det, loaded=True)
        sid = _enroll(client, auth, "1", "A", e, det)
        cid, _ = _course(client, auth, [sid])
        assert _post_session(client, auth, cid).status_code == 201


class TestFiles:
    def test_requires_auth_and_blocks_traversal(self, client, auth):
        assert client.get("/files/sessions/1/original.jpg").status_code == 401
        # The HTTP client normalizes "../" away, so exercise the handler directly as well.
        from fastapi import HTTPException
        from app.main import serve_file
        for bad in ("../app.sqlite3", "sessions/../app.sqlite3", "sessions/../../etc/passwd", "tmp/x", "app.sqlite3"):
            with pytest.raises(HTTPException) as exc:
                serve_file(bad, None)
            assert exc.value.status_code in (403, 404), bad
        for bad in ("sessions/..%2fapp.sqlite3", "%2e%2e/app.sqlite3", "tmp/x"):
            r = client.get(f"/files/{bad}", headers=auth)
            assert r.status_code in (403, 404), (bad, r.status_code)
            assert not r.content.startswith(b"SQLite format")
        assert client.get("/files/sessions/999/original.jpg", headers=auth).status_code == 404

    def test_unknown_api_path_is_json_404(self, client, auth):
        r = client.get("/api/does-not-exist", headers=auth)
        assert r.status_code == 404 and r.json()["code"] == "NOT_FOUND"


class TestDecode:
    def test_mpo_phone_jpeg_accepted(self):
        buf = io.BytesIO()
        Image.new("RGB", (64, 64), (10, 20, 30)).save(buf, format="MPO")
        assert decode_image(buf.getvalue()).shape == (64, 64, 3)

    def test_gif_rejected(self):
        buf = io.BytesIO()
        Image.new("RGB", (8, 8)).save(buf, format="GIF")
        with pytest.raises(ValueError):
            decode_image(buf.getvalue())


class TestFinetunedOnnxDecode:
    def test_letterbox_roundtrip(self):
        """A box predicted in letterboxed 640x640 space must map back to original pixels."""
        det = FinetunedDetector(model_path=__import__("pathlib").Path("x.onnx"), pretrained=MagicMock())
        det._input_size = 640
        orig_w, orig_h = 1280, 640           # ratio 0.5 -> 640x320, pad_y = 160
        # face at x 400..500, y 200..300 in the original image
        cx, cy, bw, bh = 450 * 0.5, 250 * 0.5 + 160, 100 * 0.5, 100 * 0.5
        out = np.zeros((1, 5, 10), np.float32)
        out[0, :, 0] = [cx, cy, bw, bh, 0.9]
        sess = MagicMock()
        sess.get_inputs.return_value = [MagicMock(name="images")]
        sess.run.return_value = [out]
        det._onnx_session = sess
        boxes = det._run_onnx(np.zeros((orig_h, orig_w, 3), np.uint8))
        assert len(boxes) == 1
        x1, y1, x2, y2, conf = boxes[0]
        assert abs(x1 - 400) < 3 and abs(x2 - 500) < 3 and abs(y1 - 200) < 3 and abs(y2 - 300) < 3
        assert conf == pytest.approx(0.9)


class TestEnrollmentMultiscale:
    def test_falls_back_to_other_det_sizes_and_restores_size(self):
        from app.services.enrollment import detect_faces_multiscale
        app = MagicMock()
        app.det_model.input_size = (1280, 1280)
        seen = []

        def fake_get(_img):
            seen.append(app.det_model.input_size)
            return [] if len(seen) < 2 else ["face"]

        app.get.side_effect = fake_get
        out = detect_faces_multiscale(app, np.zeros((10, 10, 3), np.uint8))
        assert out == ["face"] and seen == [(640, 640), (320, 320)]
        assert app.det_model.input_size == (1280, 1280)      # restored for class photos

    def test_no_face_at_any_size(self):
        from app.services.enrollment import detect_faces_multiscale
        app = MagicMock()
        app.get.return_value = []
        assert detect_faces_multiscale(app, np.zeros((10, 10, 3), np.uint8)) == []
        assert app.get.call_count == 2  # ENROLL_DET_SIZES = (640, 320)
