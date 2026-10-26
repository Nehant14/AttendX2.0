"""Script to seed admin user directly from CLI."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.config import settings
from app.db import SessionLocal, init_db
from app.models import User
from app.security import hash_password


def main():
    init_db()
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == settings.ADMIN_EMAIL))
        if admin is not None:
            print(f"Admin user '{settings.ADMIN_EMAIL}' already exists.")
            return

        user = User(
            email=settings.ADMIN_EMAIL,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            role="admin",
        )
        db.add(user)
        db.commit()
        print(f"Seeded admin user: {settings.ADMIN_EMAIL}")


if __name__ == "__main__":
    main()
