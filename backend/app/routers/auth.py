"""Authentication endpoints: login and current-user."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserOut
from app.security import create_access_token, get_current_user, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.email) == body.email.strip().lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user.id, user.email, user.role)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
def me(current=Depends(get_current_user), db: Session = Depends(get_db)):
    if current is None:
        # AUTH_ENABLED=false; return a synthetic user
        return UserOut(id=0, email="demo@example.com", role="admin")
    user = db.get(User, int(current["sub"]))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return UserOut.model_validate(user)
