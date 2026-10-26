"""Tests for Student API endpoints."""
from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from app.config import settings
from app.routers import health
from app.security import create_access_token
from tests.conftest import create_test_image_bytes


@pytest.fixture
def auth_headers():
    token = create_access_token(user_id=1, email="test@example.com", role="admin")
    return {"Authorization": f"Bearer {token}"}


class TestStudentAPI:
    def test_create_student_success(self, client, auth_headers):
        payload = {
            "roll_no": "CS2026-001",
            "full_name": "Alice Johnson",
            "email": "alice@example.com",
            "consent_recorded": True,
            "consent_date": "2026-10-21",
        }
        res = client.post("/api/students", json=payload, headers=auth_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["roll_no"] == "CS2026-001"
        assert data["full_name"] == "Alice Johnson"
        assert data["ready"] is False
        assert data["embedding_count"] == 0

    def test_create_duplicate_roll_no_conflict(self, client, auth_headers):
        payload = {
            "roll_no": "CS2026-DUP",
            "full_name": "Bob Smith",
        }
        res1 = client.post("/api/students", json=payload, headers=auth_headers)
        assert res1.status_code == 201

        res2 = client.post("/api/students", json=payload, headers=auth_headers)
        assert res2.status_code == 409
        assert res2.json()["code"] == "DUPLICATE"

    def test_list_and_search_students(self, client, auth_headers):
        client.post("/api/students", json={"roll_no": "R01", "full_name": "Charlie Chaplin"}, headers=auth_headers)
        client.post("/api/students", json={"roll_no": "R02", "full_name": "David Copperfield"}, headers=auth_headers)

        res = client.get("/api/students", headers=auth_headers)
        assert res.status_code == 200
        assert len(res.json()) >= 2

        search_res = client.get("/api/students?query=Chaplin", headers=auth_headers)
        assert search_res.status_code == 200
        items = search_res.json()
        assert len(items) == 1
        assert items[0]["full_name"] == "Charlie Chaplin"

    def test_update_student(self, client, auth_headers):
        c_res = client.post("/api/students", json={"roll_no": "R10", "full_name": "Original Name"}, headers=auth_headers)
        sid = c_res.json()["id"]

        u_res = client.patch(f"/api/students/{sid}", json={"full_name": "Updated Name"}, headers=auth_headers)
        assert u_res.status_code == 200
        assert u_res.json()["full_name"] == "Updated Name"

    def test_soft_delete_and_purge(self, client, auth_headers):
        c_res = client.post("/api/students", json={"roll_no": "R20", "full_name": "Delete Me"}, headers=auth_headers)
        sid = c_res.json()["id"]

        # Soft delete
        del_res = client.delete(f"/api/students/{sid}?purge=false", headers=auth_headers)
        assert del_res.status_code == 204

        # Student should now be inactive
        get_res = client.get(f"/api/students/{sid}", headers=auth_headers)
        assert get_res.status_code == 200
        assert get_res.json()["is_active"] is False

        # Hard purge
        del_res2 = client.delete(f"/api/students/{sid}?purge=true", headers=auth_headers)
        assert del_res2.status_code == 204

        # Student should now be 404
        get_res2 = client.get(f"/api/students/{sid}", headers=auth_headers)
        assert get_res2.status_code == 404

    def test_upload_photos_mocked(self, client, auth_headers):
        c_res = client.post("/api/students", json={"roll_no": "R30", "full_name": "Photo Test"}, headers=auth_headers)
        sid = c_res.json()["id"]

        # Set mock detector
        mock_det = MagicMock()
        mock_det.is_loaded = True
        mock_app = MagicMock()

        # Mock face
        mock_face = MagicMock()
        mock_face.det_score = 0.95
        mock_face.bbox = np.array([20, 20, 160, 160], dtype=np.float32)
        norm_emb = np.random.randn(512).astype(np.float32)
        norm_emb = norm_emb / np.linalg.norm(norm_emb)
        mock_face.normed_embedding = norm_emb
        mock_app.get.return_value = [mock_face]
        mock_det.get_app.return_value = mock_app
        mock_det.embedder_version = "arcface-buffalo_l"

        health.set_detector(mock_det, loaded=True)

        img_bytes = create_test_image_bytes(w=200, h=200)
        files = [("files", ("photo1.jpg", img_bytes, "image/jpeg"))]

        with patch("app.services.enrollment.compute_blur_variance", return_value=120.0):
            res = client.post(f"/api/students/{sid}/photos", files=files, headers=auth_headers)

        assert res.status_code == 200
        data = res.json()
        assert data["embedding_count"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["accepted"] is True
