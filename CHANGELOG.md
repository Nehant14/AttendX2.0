# Review & fix log

Everything below was found by reading the code against the master plan and then running it
(unit tests, a live server with the real `buffalo_l` model, and component tests).

## Security
- `/files/sessions/../attendance.sqlite3` could serve the SQLite database to a logged-in user.
  Files are now served only from `enrollment/` and `sessions/`, `..` segments are rejected and the
  resolved path must stay inside that folder (regression test included).
- SPA catch-all no longer allows `..` paths and returns JSON 404 for unknown `/api` and `/files` paths.
- `APP_ENV=prod` now refuses to start with the default `SECRET_KEY` / `ADMIN_PASSWORD`.

## Backend bugs
- `sessions.py` used `np` before importing it (crash on the first attendance run).
- `DET_CONF_MIN` was never applied: InsightFace's own 0.5 cutoff was used. Now passed as `det_thresh`.
- **Enrollment failed on close-up/selfie photos**: SCRFD at `DET_SIZE=1280` misses faces that fill the
  frame (and hallucinated tiny faces). Enrollment and the calibration script now try 640, 320, 960.
- Course roster `PUT` returned an empty/stale student list (stale ORM collection).
- `HTTPException` responses (401, 404...) lacked the documented `code`; validation errors were not in
  `{detail, code}` form. Added handlers for all of them.
- `replace=true` deleted the old session's files before the new one succeeded. The new session is now
  built in a temp folder and swapped in only on success (old session survives any failure).
- Phone JPEGs reported by Pillow as `MPO` were rejected as unsupported.
- Students enrolled in a course but without photos got no attendance row; they are now `absent`.
- Unsupported/corrupt uploads returned 422 instead of 415; size/type are validated before any work.
- Enrollment ran inference on the event loop without the global lock and saved photos without EXIF
  rotation; it now runs in the thread pool under the lock and saves the rotated image.
- `PATCH /students` could not clear `email`/consent date; creating students with blank names is rejected.
- `FinetunedDetector` had no `get_app()` (enrollment broke in finetuned mode), ONNX input was stretched
  instead of letterboxed, and crops used the 1280 detector size instead of 320.
- Stored file paths are now relative to `DATA_DIR`; `created_by` no longer violates the FK for unknown users.
- Added `student_id` filters to `GET /api/sessions` and `GET /api/attendance/summary` (History page).
- Login is case-insensitive on e-mail.

## Frontend bugs
- Images and CSV downloads used plain `<img>`/`<a>` and returned 401 whenever login was enabled.
  Added authenticated image loading (`AuthImage`) and `downloadFile`.
- Student detail page crashed after saving (PATCH response has no `photos`); consent date was overwritten
  on every save; "Activate" never worked (it always called DELETE).
- Wrong password showed "Unauthorized"; now shows the server message.
- Dates used UTC (`toISOString`), giving the wrong day for part of every day in India.
- No navigation on phones; zoom wheel scrolled the page; touch panning did not work.
- Indeterminate progress bar had no keyframes; History page lacked the student filter; error states added.
- Login page is skipped when `AUTH_ENABLED=false`.

## Tooling / infra
- Tests no longer load the real model or touch the real database (`SKIP_MODEL_LOAD`, temp `DATA_DIR`).
- A stray `backend/data/attendance.sqlite3` that shipped in the zip was removed; added `.dockerignore`.
- ml/finetune: `--limit` now writes up to N images (images without faces no longer reduce the count).
- Calibration/seed scripts can be run as `python scripts/<name>.py` from `backend/`.
- README corrected (ArcFace is ResNet-50 in `buffalo_l`) and extended.

## Verification performed
- Backend: 53 tests (52 + 1 integration test needing the real model and `onnx`).
- Frontend: 9 component tests, `tsc --noEmit`, production build.
- Live server with real `buffalo_l`: 5 enrolled people matched to their own faces (similarity 0.97-0.99),
  an un-enrolled face reported `unknown`, a student without photos `absent`; replace/409/override/CSV/history OK.
- Finetuned detector path verified with a synthetic ONNX model (boxes within 1 px, NMS and confidence filter OK).
- Not verified here: Docker image build, a real browser session, a real fine-tuned model.
