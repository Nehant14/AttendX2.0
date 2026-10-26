# AttendX 2.0 — Automated Classroom Attendance System

AttendX 2.0 is a full-stack, AI-powered classroom attendance application. A teacher uploads a single photo of a classroom, and the system:
1. Detects every face in the photo (using pretrained SCRFD or optional fine-tuned YOLOv8-face).
2. Extracts 512-dimensional ArcFace face embeddings.
3. Matches students against enrolled face templates using cosine similarity and the Hungarian one-to-one optimal assignment algorithm.
4. Color-codes and annotates the classroom photo.
5. Produces date-wise attendance records with teacher manual overrides, cumulative reports, and Excel-compatible CSV exports.

---

## 1. Screenshots Placeholder

| Take Attendance | Annotated Result & Roster Review |
|---|---|
| ![Take Attendance Preview](docs/screenshots/take_attendance.png) | ![Annotated Preview](docs/screenshots/session_result.png) |

---

## 2. Requirements

- **Docker & Docker Compose** (Recommended for single-command run)
- **Python**: 3.10 or 3.11 (for local backend development)
- **Node.js**: 20 LTS (for local frontend development)
- **RAM**: Minimum 4 GB recommended for model inference

---

## 3. Quick Start with Docker

```bash
# 1. Clone or navigate to the repository
cd attendance-app

# 2. Copy environment template
cp .env.example .env

# 3. Configure secrets and password
# Edit .env and set SECRET_KEY, ADMIN_PASSWORD

# 4. Start the container
docker compose up --build

# 5. Open your browser
# Visit http://localhost:8000
```

---

## 4. Local Development Setup

To run backend and frontend separately during active development:

### Backend (Terminal 1)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate

pip install -r requirements.txt
cp ../.env.example .env      # the backend reads backend/.env when started from backend/

uvicorn app.main:app --reload --port 8000
```

### Frontend (Terminal 2)
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```
*Note: Vite dev proxy automatically forwards `/api` and `/files` to `http://localhost:8000`.*

To serve the UI from the backend instead (single port, as in Docker), run `npm run build` in `frontend/` and open `http://localhost:8000`.

Set `APP_ENV=prod` only with a real `SECRET_KEY` (24+ characters) and a changed `ADMIN_PASSWORD`; in prod mode the app refuses to start with the defaults.

---

## 5. Model Download Behaviour

- **InsightFace Pretrained Weights (`buffalo_l`)**:
  On first application startup, InsightFace automatically downloads the `buffalo_l` model bundle (SCRFD face detector and an ArcFace face recognizer (ResNet-50, `w600k_r50`, 512-d embeddings)) into `~/.insightface/models/buffalo_l/`.
  - **Internet access is required once** on first run to download weights (~280 MB).
  - In Docker, a persistent volume (`insightface_cache`) mounts to `/root/.insightface` so models are never re-downloaded between container restarts.

- **Fine-Tuned Model (`models/face_ft_best.onnx`)**:
  The fine-tuned model is an optional exercise and is **never** downloaded automatically. If you wish to use it, export or place the ONNX file into `models/`.

---

## 6. Fine-Tuned Detector Integration

AttendX supports switching face detectors via configuration:

```env
DETECTOR=finetuned
FINETUNED_MODEL_PATH=models/face_ft_best.onnx
```

### Key architecture notes:
- The fine-tuned detector performs **face localization only** (finding face bounding boxes).
- ArcFace (InsightFace) is **always used for face recognition and identity embeddings** by cropping and aligning detected faces.
- If `DETECTOR=pretrained` (default), the standard InsightFace SCRFD detector is used.
- If `DETECTOR=finetuned` and the file at `FINETUNED_MODEL_PATH` is missing, the application **refuses to start** with an explicit error to prevent silent fallback.

---

## 7. First-Time Walkthrough

1. **Sign In**: Navigate to `/login` and sign in using the seeded teacher account:
   - Email: `admin@example.com` (or value of `ADMIN_EMAIL` in `.env`)
   - Password: value of `ADMIN_PASSWORD` in `.env`
2. **Add Students**:
   - Go to **Students** &rarr; **Add Student**.
   - Fill in roll number and student name. Record biometric consent in compliance with DPDP standards.
3. **Enroll Face Photos**:
   - Click **Manage** on a student.
   - Upload **5 to 10 photos** per student with varied angles, lighting, and expressions.
   - Each photo undergoes automatic quality checks: face size, sharpness (Laplacian variance), single face verification, and duplicate identity alerts.
   - Enrollment photos are close-ups, so detection tries several detector input sizes (640, 320, then 960). The class-photo size (`DET_SIZE`, default 1280) misses faces that fill most of the frame.
   - Students with no accepted photos still appear on every attendance sheet as **Absent**, and you can mark them present manually.
4. **Create a Course**:
   - Go to **Courses** &rarr; **Create Course** (e.g., `CS101`).
   - Assign the enrolled students to the course roster.
5. **Take Attendance**:
   - Go to **Take Attendance**.
   - Select the course, date, and period slot.
   - Upload a class photo and click **Recognize Faces & Record Attendance**.
6. **Review & Override**:
   - Inspect the interactive zoomable image viewer.
   - Ambiguous or low-margin faces appear in yellow as **Needs Review**.
   - Use the dropdown on any row to override status to Present or Absent (marked by "teacher").
7. **Export & History**:
   - Click **Export CSV** to download Excel-ready reports with UTF-8 BOM encoding.
   - **History** filters by course, student and date range; the same filters apply to the CSV export and the per-student percentage summary.

---

## 8. Running Automated Tests

Backend (no models or internet needed; the tests use a temporary database and mocked detector):

```bash
cd backend
pytest -v
```

Frontend (component tests with a mocked API, plus the TypeScript type-check):

```bash
cd frontend
npm test
npx tsc --noEmit
```

Tests include:
- `test_matcher.py`: Hungarian one-to-one assignment, similarity thresholds, margin requirement, lookalike handling, K=1 and N>K edge cases.
- `test_enrollment_quality.py`: Multiple faces check, blur variance thresholds, small face rejection, confidence filtering.
- `test_export.py`: UTF-8 BOM verification, Excel compatibility, formatted similarity scores.
- `test_api_students.py`: Student CRUD, duplicate roll number rejection (409), photo upload lifecycle.
- `test_api_sessions.py`: Complete attendance lifecycle, duplicate overwrite protection (replace=true), overrides, CSV exports.
- `test_regressions.py`: error format (`detail` + `code`), roster replacement, safe `replace=true` (a failed replace keeps the old session), students without photos, `/files` path-traversal protection, MPO phone JPEGs, ONNX letterbox decoding, multi-scale enrollment detection.

---

## 9. Threshold Calibration

Default recognition thresholds in `.env` (`SIM_ACCEPT=0.45`, `SIM_REVIEW_MIN=0.35`, `MARGIN_MIN=0.05`) are solid starting baselines.

To empirically calibrate thresholds for your specific camera hardware and room lighting:
1. Collect a folder of consented calibration photos: `calibration/<student_name>/*.jpg` (at least 3-10 photos per student).
2. Run the calibration script:
   ```bash
   cd backend
   python scripts/calibrate_thresholds.py --dir calibration
   ```
   Use real photos taken on different days and in different lighting. The default numbers are starting points only; measure them for your own camera and room.
3. The script evaluates all genuine pairs (same person) and impostor pairs (different people), reports False Accept Rates (FAR) at 1% and 0.1%, and prints recommended `SIM_ACCEPT` and `SIM_REVIEW_MIN` values to copy into `.env`.

---

## 10. Fine-Tuning Exercise

See [`ml/finetune/README.md`](ml/finetune/README.md) for full instructions on fine-tuning YOLOv8 on WIDER FACE with a conservative, capability-preserving training schedule.

---

## 11. Troubleshooting & Known Pitfalls

| Issue | Cause & Resolution |
|---|---|
| **InsightFace build failure** | Ensure `build-essential`, `libgl1`, and `libglib2.0-0` are installed on Linux, or use the provided Docker container. |
| **NumPy ABI error** | Pin `numpy<2` as specified in `requirements.txt`. |
| **Models not found on startup** | Ensure internet connectivity on the first run for InsightFace to download weights to `~/.insightface`. |
| **Rotated photos give 0 faces** | AttendX automatically applies Pillow EXIF transpose before face detection. |
| **Enrollment says "No face detected" for a clear selfie** | Fixed by multi-scale detection (see section 7). If it still happens, the face is probably tiny, heavily rotated or covered; retake the photo closer and facing the camera. |
| **Many faces marked unknown** | Increase photo resolution, ensure classroom is well-lit, or adjust `SIM_ACCEPT` lower after calibration. |
| **Lookalike misidentification** | Increase `MARGIN_MIN` (e.g. `0.08`) and upload more diverse enrollment photos per student. |
| **Images or CSV exports return 401** | The session token expired; sign in again. Files are only served to logged-in users (the UI loads them with the token). |
| **Database locked error** | SQLite runs with WAL mode (`PRAGMA journal_mode=WAL`) and a single Uvicorn worker process. |

---

## 12. Privacy, Ethics & Limitations

- **Biometric Personal Data**: Face embeddings are biometric identifiers. AttendX requires recording explicit student consent (`consent_recorded`). Under India's Digital Personal Data Protection (DPDP) Act, a permanent deletion route (`DELETE /api/students/{id}?purge=true`) is provided to remove embeddings, photos, and records upon request.
- **Assistive System**: Automated attendance is an assistive tool for educators. Ambiguous detections are flagged for manual review rather than falsely recorded.
- **Limitations**:
  - No liveness detection (anti-spoofing): printed photos could match enrolled students.
  - There is no login rate limiting; run the app on a trusted network or behind a reverse proxy.
  - Lookalikes (siblings, twins) can be confused; they usually land in **Needs Review**, but always check yellow rows.
  - Distant back-row students with face width < 40 pixels are marked `unrecognizable` to avoid false guesses.
- **Licensing**: InsightFace pretrained weights are intended for non-commercial research and educational use. Ultralytics YOLO is licensed under AGPL-3.0.
