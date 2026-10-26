"""Pydantic request/response schemas."""
from __future__ import annotations
import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


# ─── Auth ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ─── Students ────────────────────────────────────────────────────────────────

def _strip_required(v: str) -> str:
    v = (v or "").strip()
    if not v:
        raise ValueError("must not be empty")
    return v


class StudentCreate(BaseModel):
    roll_no: str
    full_name: str
    email: Optional[str] = None
    consent_recorded: bool = False
    consent_date: Optional[datetime.date] = None

    @field_validator("roll_no", "full_name")
    @classmethod
    def _required(cls, v: str) -> str:
        return _strip_required(v)

    @field_validator("email")
    @classmethod
    def _email(cls, v: Optional[str]) -> Optional[str]:
        v = (v or "").strip()
        return v or None


class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    consent_recorded: Optional[bool] = None
    consent_date: Optional[datetime.date] = None

    @field_validator("full_name")
    @classmethod
    def _name(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else _strip_required(v)


class PhotoOut(BaseModel):
    id: int
    url: str
    det_score: Optional[float]
    face_px: Optional[int]
    model_config = {"from_attributes": True}


class StudentOut(BaseModel):
    id: int
    roll_no: str
    full_name: str
    email: Optional[str]
    is_active: bool
    consent_recorded: bool
    consent_date: Optional[datetime.date]
    embedding_count: int = 0
    ready: bool = False
    model_config = {"from_attributes": True}


class StudentDetailOut(StudentOut):
    photos: list[PhotoOut] = []


class PhotoUploadResult(BaseModel):
    filename: str
    accepted: bool
    reason: Optional[str] = None
    embedding_id: Optional[int] = None


class PhotoUploadResponse(BaseModel):
    results: list[PhotoUploadResult]
    embedding_count: int
    ready: bool
    warnings: list[str] = []


# ─── Courses ─────────────────────────────────────────────────────────────────

class CourseCreate(BaseModel):
    code: str
    name: str

    @field_validator("code", "name")
    @classmethod
    def _required(cls, v: str) -> str:
        return _strip_required(v)


class CourseOut(BaseModel):
    id: int
    code: str
    name: str
    student_count: int = 0
    model_config = {"from_attributes": True}


class CourseDetailOut(CourseOut):
    students: list[StudentOut] = []


class RosterUpdate(BaseModel):
    student_ids: list[int]


# ─── Sessions ────────────────────────────────────────────────────────────────

class AttendanceRecordOut(BaseModel):
    student_id: int
    roll_no: str
    full_name: str
    status: str
    similarity: Optional[float]
    margin: Optional[float]
    bbox: Optional[list[float]]
    marked_by: str
    model_config = {"from_attributes": True}


class UnmatchedFaceOut(BaseModel):
    bbox: list[float]
    label: str
    det_score: float


class CountsOut(BaseModel):
    enrolled: int
    faces_detected: int
    present: int
    needs_review: int
    absent: int
    unknown_faces: int
    unrecognizable_faces: int


class SessionOut(BaseModel):
    id: int
    course: CourseOut
    session_date: datetime.date
    period: int
    status: str
    detector_version: Optional[str]
    embedder_version: Optional[str]
    counts: CountsOut
    banner: Optional[str]
    original_url: Optional[str]
    annotated_url: Optional[str]
    records: list[AttendanceRecordOut]
    unmatched_faces: list[UnmatchedFaceOut]
    processing_ms: Optional[int]
    model_config = {"from_attributes": True}


class SessionSummaryOut(BaseModel):
    id: int
    course_id: int
    course_code: str
    session_date: datetime.date
    period: int
    status: str
    faces_detected: int
    present: int
    absent: int
    needs_review: int
    model_config = {"from_attributes": True}


class RecordPatch(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("present", "absent"):
            raise ValueError("status must be 'present' or 'absent'")
        return v


# ─── Attendance history ───────────────────────────────────────────────────────

class AttendanceRowOut(BaseModel):
    session_id: int
    session_date: datetime.date
    period: int
    course_code: str
    roll_no: str
    full_name: str
    status: str
    marked_by: str


class AttendanceSummaryOut(BaseModel):
    roll_no: str
    full_name: str
    sessions: int
    present: int
    absent: int
    percent: float


# ─── Health ──────────────────────────────────────────────────────────────────

class HealthOut(BaseModel):
    status: str
    detector: str
    embedder: str
    models_loaded: bool
    students: int
    embeddings: int
