"""Tests for Session and Attendance API endpoints."""
from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from app.routers import health
from app.security import create_access_token
from app.services.detector import FaceDetection
from tests.conftest import create_test_image_bytes, make_unit_vector


@pytest.fixture
def auth_headers():
    token = create_access_token(user_id=1, email="admin@example.com", role="admin")
    return {"Authorization": f"Bearer {token}"}


class TestSessionAPI:
    def test_session_lifecycle(self, client, auth_headers):
        # 1. Create Course
        c_res = client.post("/api/courses", json={"code": "MATH101", "name": "Calculus I"}, headers=auth_headers)
        assert c_res.status_code == 201
        course_id = c_res.json()["id"]

        # 2. Create Student
        s_res = client.post("/api/students", json={"roll_no": "M001", "full_name": "Euler"}, headers=auth_headers)
        student_id = s_res.json()["id"]

        # 3. Assign Student to Course
        r_res = client.put(f"/api/courses/{course_id}/students", json={"student_ids": [student_id]}, headers=auth_headers)
        assert r_res.status_code == 200
        assert r_res.json()["student_count"] == 1

        # 4. Enroll a photo for student to give them an embedding
        student_emb = make_unit_vector(seed=42)
        mock_det = MagicMock()
        mock_det.is_loaded = True
        mock_det.version = "scrfd-buffalo_l"
        mock_det.embedder_version = "arcface-buffalo_l"
        mock_app = MagicMock()

        mock_face = MagicMock()
        mock_face.det_score = 0.92
        mock_face.bbox = np.array([20, 20, 160, 160], dtype=np.float32)
        mock_face.normed_embedding = student_emb
        mock_app.get.return_value = [mock_face]
        mock_det.get_app.return_value = mock_app

        health.set_detector(mock_det, loaded=True)

        img_bytes = create_test_image_bytes()
        with patch("app.services.enrollment.compute_blur_variance", return_value=100.0):
            p_res = client.post(
                f"/api/students/{student_id}/photos",
                files=[("files", ("euler.jpg", img_bytes, "image/jpeg"))],
                headers=auth_headers,
            )
        assert p_res.status_code == 200

        # 5. Take Attendance Session
        # Mock detector.detect on the class photo to detect Euler's face
        class_face = FaceDetection(
            bbox=[50.0, 50.0, 200.0, 200.0],
            det_score=0.95,
            kps=None,
            embedding=student_emb,  # Same embedding -> high match!
            face_px=150,
        )
        mock_det.detect.return_value = [class_face]

        sess_data = {
            "course_id": course_id,
            "session_date": "2026-10-21",
            "period": 1,
            "replace": False,
        }
        files = {"file": ("class_photo.jpg", img_bytes, "image/jpeg")}

        sess_res = client.post("/api/sessions", data=sess_data, files=files, headers=auth_headers)
        assert sess_res.status_code == 201
        s_data = sess_res.json()
        session_id = s_data["id"]
        assert s_data["status"] == "done"
        assert s_data["counts"]["present"] == 1
        assert s_data["records"][0]["status"] == "present"

        # 6. Duplicate session without replace -> 409
        dup_res = client.post("/api/sessions", data=sess_data, files=files, headers=auth_headers)
        assert dup_res.status_code == 409
        assert dup_res.json()["code"] == "SESSION_EXISTS"

        # 7. Duplicate session WITH replace=true -> 201
        sess_data["replace"] = True
        rep_res = client.post("/api/sessions", data=sess_data, files=files, headers=auth_headers)
        assert rep_res.status_code == 201
        new_session_id = rep_res.json()["id"]

        # 8. Teacher override PATCH
        patch_res = client.patch(
            f"/api/sessions/{new_session_id}/records/{student_id}",
            json={"status": "absent"},
            headers=auth_headers,
        )
        assert patch_res.status_code == 200
        patch_data = patch_res.json()
        assert patch_data["records"][0]["status"] == "absent"
        assert patch_data["records"][0]["marked_by"] == "teacher"

        # 9. Attendance history summary
        hist_res = client.get(f"/api/attendance?course_id={course_id}", headers=auth_headers)
        assert hist_res.status_code == 200
        assert len(hist_res.json()) >= 1

        sum_res = client.get(f"/api/attendance/summary?course_id={course_id}", headers=auth_headers)
        assert sum_res.status_code == 200
        assert sum_res.json()[0]["roll_no"] == "M001"

        # 10. Export CSV
        csv_res = client.get(f"/api/sessions/{new_session_id}/export.csv", headers=auth_headers)
        assert csv_res.status_code == 200
        assert "text/csv" in csv_res.headers["content-type"]
        assert b"M001" in csv_res.content

        # 11. Delete Session
        del_res = client.delete(f"/api/sessions/{new_session_id}", headers=auth_headers)
        assert del_res.status_code == 204

        get_res = client.get(f"/api/sessions/{new_session_id}", headers=auth_headers)
        assert get_res.status_code == 404
