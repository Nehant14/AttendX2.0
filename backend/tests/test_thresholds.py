"""Absent students keep their match scores; thresholds can be re-applied and are saved."""
import numpy as np
import pytest

from app.routers import health
from app.services.matcher import decide_status, student_best_scores
from tests.conftest import make_unit_vector
from tests.test_regressions import _course, _enroll, _mock_detector, _post_session, auth  # noqa: F401


def _blend(a, b, wa, wb):
    v = wa * a + wb * b
    return (v / np.linalg.norm(v)).astype(np.float32)


@pytest.fixture
def scene(client, auth):
    """Two students; the one face in the photo looks mostly like A and somewhat like B."""
    ea, eb = make_unit_vector(seed=11), make_unit_vector(seed=12)
    face = _blend(ea, eb, 0.8, 0.6)
    det = _mock_detector([face])
    health.set_detector(det, loaded=True)
    a = _enroll(client, auth, "1", "Alice", ea, det)
    b = _enroll(client, auth, "2", "Bob", eb, det)
    cid, _ = _course(client, auth, [a, b])
    r = _post_session(client, auth, cid)
    assert r.status_code == 201, r.text
    return r.json()


def _by_roll(body):
    return {r["roll_no"]: r for r in body["records"]}


def test_absent_student_still_has_scores(scene):
    rec = _by_roll(scene)
    assert rec["1"]["status"] == "present"
    assert rec["2"]["status"] == "absent"
    assert rec["2"]["similarity"] is not None and 0.4 < rec["2"]["similarity"] < 0.8
    assert rec["2"]["margin"] is not None and rec["2"]["margin"] < 0   # Alice fits the face better


def test_session_exposes_default_thresholds(scene):
    assert scene["thresholds"] == {"sim_accept": 0.45, "sim_review_min": 0.35, "margin_min": 0.05}


def test_rescore_is_saved_and_one_face_goes_to_one_student(client, auth, scene):
    sid = scene["id"]
    # Very permissive: Bob would pass on score alone, but Alice already owns the only face.
    r = client.post(f"/api/sessions/{sid}/rescore", headers=auth,
                    json={"sim_accept": 0.1, "sim_review_min": 0.05, "margin_min": -1.0})
    assert r.status_code == 200
    rec = _by_roll(r.json())
    assert rec["1"]["status"] == "present" and rec["2"]["status"] == "absent"

    # Strict: Alice falls to review. Saved, so a fresh GET shows the same.
    r = client.post(f"/api/sessions/{sid}/rescore", headers=auth,
                    json={"sim_accept": 0.95, "sim_review_min": 0.5, "margin_min": 0.05})
    assert _by_roll(r.json())["1"]["status"] == "needs_review"
    again = client.get(f"/api/sessions/{sid}", headers=auth).json()
    assert _by_roll(again)["1"]["status"] == "needs_review"


def test_rescore_never_overwrites_teacher_marks(client, auth, scene):
    sid = scene["id"]
    bob = _by_roll(scene)["2"]["student_id"]
    client.patch(f"/api/sessions/{sid}/records/{bob}", headers=auth, json={"status": "present"})
    r = client.post(f"/api/sessions/{sid}/rescore", headers=auth,
                    json={"sim_accept": 0.99, "sim_review_min": 0.98, "margin_min": 0.5})
    rec = _by_roll(r.json())
    assert rec["2"]["status"] == "present" and rec["2"]["marked_by"] == "teacher"
    assert rec["1"]["status"] == "absent"


def test_rescore_validates_thresholds(client, auth, scene):
    sid = scene["id"]
    bad = client.post(f"/api/sessions/{sid}/rescore", headers=auth,
                      json={"sim_accept": 0.3, "sim_review_min": 0.6, "margin_min": 0.0})
    assert bad.status_code == 422
    out_of_range = client.post(f"/api/sessions/{sid}/rescore", headers=auth,
                               json={"sim_accept": 5, "sim_review_min": 0.1, "margin_min": 0.0})
    assert out_of_range.status_code == 422


def test_image_urls_survive_windows_style_stored_paths(client, auth, scene, db_session):
    from app.models import AttendanceSession
    sess = db_session.get(AttendanceSession, scene["id"])
    sess.source_image_path = "data\\sessions\\%d\\original.jpg" % sess.id
    sess.annotated_image_path = "C:\\old\\proj\\data\\sessions\\%d\\annotated.jpg" % sess.id
    db_session.commit()
    body = client.get(f"/api/sessions/{sess.id}", headers=auth).json()
    for key in ("original_url", "annotated_url"):
        assert client.get(body[key], headers=auth).status_code == 200


def test_unit_helpers():
    assert decide_status(0.6, 0.2, 0.45, 0.35, 0.05) == "present"
    assert decide_status(0.6, 0.0, 0.45, 0.35, 0.05) == "needs_review"
    assert decide_status(0.2, 0.9, 0.45, 0.35, 0.05) == "absent"
    assert student_best_scores(np.zeros((0, 4), np.float32), np.zeros((0, 4), np.float32),
                               np.array([]), 2) == [None, None]
