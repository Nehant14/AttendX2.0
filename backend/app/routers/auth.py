"""Login (admin or student) and the JWT dependencies used by the other routers."""
import datetime

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Student
from app.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"


def _token(role: str, name: str, student_id: int | None = None) -> str:
    exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"role": role, "name": name, "student_id": student_id, "exp": exp},
        settings.SECRET_KEY, algorithm=ALGORITHM,
    )


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    username = body.username.strip()

    # Admin / professor: credentials from .env
    if username.lower() == settings.ADMIN_EMAIL.lower() and body.password == settings.ADMIN_PASSWORD:
        return LoginResponse(access_token=_token("admin", "Admin"), role="admin", name="Admin")

    # Student: username = roll number, password = roll number
    student = db.scalar(select(Student).where(Student.roll_no == username))
    if student is not None and body.password == student.roll_no:
        return LoginResponse(
            access_token=_token("student", student.full_name, student.id),
            role="student", name=student.full_name,
        )

    raise HTTPException(status_code=401, detail="Incorrect username or password.")


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    if creds is None:
        raise HTTPException(status_code=401, detail="Not logged in.")
    try:
        return jwt.decode(creds.credentials, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")


def admin_only(user: dict = Depends(current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only.")
    return user


def student_only(user: dict = Depends(current_user)) -> dict:
    if user.get("role") != "student":
        raise HTTPException(status_code=403, detail="Students only.")
    return user
