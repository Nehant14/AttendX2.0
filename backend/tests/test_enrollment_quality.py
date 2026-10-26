"""Tests for enrollment quality checks."""
import io
import numpy as np
import pytest
from PIL import Image
from unittest.mock import MagicMock, patch
from app.services.enrollment import check_enrollment_photo, compute_blur_variance


def make_white_image(w=400, h=400) -> bytes:
    img = Image.new("RGB", (w, h), color=(200, 180, 160))
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    return buf.getvalue()


def make_mock_face(det_score=0.85, bbox=(50, 50, 250, 250), normed_embedding=None):
    face = MagicMock()
    face.det_score = det_score
    x1, y1, x2, y2 = bbox
    face.bbox = np.array([x1, y1, x2, y2], dtype=np.float32)
    face.normed_embedding = normed_embedding if normed_embedding is not None else (
        np.random.randn(512).astype(np.float32)
    )
    face.normed_embedding = face.normed_embedding / np.linalg.norm(face.normed_embedding)
    return face


class TestEnrollmentQuality:
    def _make_app(self, faces):
        app = MagicMock()
        app.get.return_value = faces
        return app

    def test_no_face_detected(self):
        app = self._make_app([])
        result = check_enrollment_photo(make_white_image(), "test.jpg", app)
        assert not result.accepted
        assert "No face" in result.reason

    def test_good_photo_accepted(self):
        face = make_mock_face(det_score=0.85, bbox=(50, 50, 250, 250))
        app = self._make_app([face])
        with patch("app.services.enrollment.compute_blur_variance", return_value=150.0):
            result = check_enrollment_photo(make_white_image(), "test.jpg", app)
        assert result.accepted
        assert result.det_score == pytest.approx(0.85, abs=0.01)

    def test_low_det_score_rejected(self):
        face = make_mock_face(det_score=0.30, bbox=(50, 50, 250, 250))
        app = self._make_app([face])
        with patch("app.services.enrollment.compute_blur_variance", return_value=150.0):
            result = check_enrollment_photo(make_white_image(), "test.jpg", app)
        assert not result.accepted
        assert "confidence" in result.reason.lower()

    def test_face_too_small_rejected(self):
        face = make_mock_face(det_score=0.85, bbox=(50, 50, 80, 80))
        app = self._make_app([face])
        with patch("app.services.enrollment.compute_blur_variance", return_value=150.0):
            result = check_enrollment_photo(make_white_image(), "test.jpg", app)
        assert not result.accepted
        assert "small" in result.reason.lower()

    def test_blurry_photo_rejected(self):
        face = make_mock_face(det_score=0.85, bbox=(50, 50, 250, 250))
        app = self._make_app([face])
        with patch("app.services.enrollment.compute_blur_variance", return_value=10.0):
            result = check_enrollment_photo(make_white_image(), "test.jpg", app)
        assert not result.accepted
        assert "blur" in result.reason.lower()

    def test_two_large_faces_rejected(self):
        face1 = make_mock_face(det_score=0.90, bbox=(10, 10, 200, 200))
        face2 = make_mock_face(det_score=0.80, bbox=(210, 10, 380, 180))
        app = self._make_app([face1, face2])
        result = check_enrollment_photo(make_white_image(), "test.jpg", app)
        assert not result.accepted
        assert "Multiple" in result.reason or "multiple" in result.reason

    def test_second_small_face_accepted(self):
        face1 = make_mock_face(det_score=0.90, bbox=(10, 10, 210, 210))
        face2 = make_mock_face(det_score=0.80, bbox=(250, 10, 300, 60))
        app = self._make_app([face1, face2])
        with patch("app.services.enrollment.compute_blur_variance", return_value=150.0):
            result = check_enrollment_photo(make_white_image(), "test.jpg", app)
        assert result.accepted

    def test_invalid_image_bytes(self):
        result = check_enrollment_photo(b"not an image", "bad.jpg", MagicMock())
        assert not result.accepted


class TestBlurVariance:
    def test_sharp_image_high_variance(self):
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        img[::10, :] = 255
        img[:, ::10] = 255
        var = compute_blur_variance(img, [0, 0, 200, 200])
        assert var > 50

    def test_uniform_image_low_variance(self):
        img = np.full((200, 200, 3), 128, dtype=np.uint8)
        var = compute_blur_variance(img, [0, 0, 200, 200])
        assert var < 5
