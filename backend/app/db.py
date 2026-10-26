"""SQLAlchemy engine, session factory, Base, and init_db()."""
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    pass


# Ensure data directory exists before creating engine
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(engine, "connect")
def set_sqlite_pragmas(dbapi_conn, connection_record):
    """Enable WAL mode and foreign key enforcement on every connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def init_db() -> None:
    """Create all tables if they do not exist."""
    from app import models  # noqa: F401 — import to register ORM classes
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency: yields a DB session, commits on success, rolls back on error."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
