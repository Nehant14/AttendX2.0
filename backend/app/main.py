"""FastAPI entry point."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import init_db
from app.routers import attendance, auth, me, students
from app.services.detector import get_detector


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.detector = get_detector()  # loads the face models once
    yield


app = FastAPI(title="Attendance App", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(students.router)
app.include_router(attendance.router)
app.include_router(me.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Saved images (enrollment photos and annotated class photos)
for folder in ("enrollment", "sessions"):
    (settings.DATA_DIR / folder).mkdir(parents=True, exist_ok=True)
    app.mount(f"/files/{folder}", StaticFiles(directory=settings.DATA_DIR / folder), name=folder)

# Built frontend (after `npm run build`), so everything runs on one port
dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if (dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith(("api/", "files/")):
            raise HTTPException(404)
        return FileResponse(dist / "index.html")
