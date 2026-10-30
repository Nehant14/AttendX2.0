"""Request / response models."""
from __future__ import annotations

import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str  # admin e-mail, or a student's roll number
    password: str


class LoginResponse(BaseModel):
    access_token: str
    role: Literal["admin", "student"]
    name: str


class StudentCreate(BaseModel):
    roll_no: str
    full_name: str


class StudentOut(BaseModel):
    id: int
    roll_no: str
    full_name: str
    photo_count: int


class PhotoOut(BaseModel):
    id: int
    url: str


class StudentDetailOut(StudentOut):
    photos: list[PhotoOut]


class PhotoUploadResult(BaseModel):
    filename: str
    accepted: bool
    reason: Optional[str] = None


class PhotoUploadResponse(BaseModel):
    results: list[PhotoUploadResult]


class RecordOut(BaseModel):
    student_id: int
    roll_no: str
    full_name: str
    status: str
    similarity: Optional[float] = None


class SessionOut(BaseModel):
    id: int
    created_at: datetime.datetime
    total: int
    present: int
    absent: int
    avg_match: Optional[float] = None  # mean similarity of the auto-matched present students
    image_url: Optional[str] = None
    records: list[RecordOut]


class StatusPatch(BaseModel):
    status: Literal["present", "absent"]


class MyRecordOut(BaseModel):
    session_id: int
    date: datetime.datetime
    status: str


class MyAttendanceOut(BaseModel):
    name: str
    roll_no: str
    total: int
    present: int
    absent: int
    percentage: float
    records: list[MyRecordOut]
