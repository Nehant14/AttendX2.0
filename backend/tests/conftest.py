"""Shared test fixtures.

Environment is configured BEFORE the app is imported so the tests never touch the real
database / data directory and never load the (slow) ML models.
"""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="attendx_test_")
os.environ["DATA_DIR"] = _TMP
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/app.sqlite3"
os.environ["SKIP_MODEL_LOAD"] = "true"
os.environ["AUTH_ENABLED"] = "true"
os.environ["APP_ENV"] = "dev"

import io
import shutil
import numpy as np
import pytest
from PIL import Image
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db import Base, get_db
from app.main import app
from app.routers import health
from fastapi.testclient import TestClient


def make_unit_vector(dim: int = 512, seed: int = 0) -> np.ndarray:
    """Create a random L2-normalized vector."""
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float32)
    return v / np.linalg.norm(v)


def create_test_image_bytes(w=200, h=200, color=(128, 128, 128)) -> bytes:
    """Generate JPEG bytes for a test image."""
    img = Image.new("RGB", (w, h), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(scope="session")
def test_temp_dir():
    yield _TMP
    shutil.rmtree(_TMP, ignore_errors=True)


@pytest.fixture(scope="function")
def db_session(test_temp_dir):
    """Create an isolated in-memory or file-based SQLite database for each test."""
    db_file = os.path.join(test_temp_dir, "test.sqlite3")
    if os.path.exists(db_file):
        os.remove(db_file)

    test_engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(test_engine, "connect")
    def set_sqlite_pragmas(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        test_engine.dispose()


@pytest.fixture(scope="function")
def client(db_session):
    """TestClient that uses the isolated db_session."""
    def override_get_db():
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    from app.services import enrollment as enroll_svc
    enroll_svc.roster_cache.rebuild([])
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    health.set_detector(None, loaded=False)
