# Face Attendance

Upload a class photo -> faces are detected (optionally with your fine-tuned detector) -> each face is
matched to the enrolled students -> present / absent list. Students log in to see their own attendance.

```
class photo -> detect faces -> ArcFace embedding -> cosine similarity vs enrolled students
            -> one-to-one assignment (Hungarian) -> match if similarity >= SIM_THRESHOLD
```

## Run

```bash
# backend (first start downloads the InsightFace models, ~280 MB)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --port 8000

# frontend (dev)
cd frontend
npm install
npm run dev            # http://localhost:5173
```

Or build once (`npm run build` in `frontend/`) and open http://localhost:8000 - the backend serves it.

## Logins (one login page)

| Who | Username | Password | Goes to |
|---|---|---|---|
| Professor / admin | `ADMIN_EMAIL` (default `admin@example.com`) | `ADMIN_PASSWORD` (default `nehant123`) | `/admin` |
| Student | roll number | roll number | `/student` |

## Pages

- **Admin** - Take Attendance (upload class photo), Students (add student, upload face photos), result page
  (class photo with boxes around every detected face, present/absent list with match %, manual Mark Present/Absent).
- **Student** - own attendance: classes, present, absent, percentage, date-wise list.

## Fine-tuned detector

Put your export in `models/face_ft_best.onnx` and set `DETECTOR=finetuned` in `.env`.
Only face *detection* changes; ArcFace is always used for identity. See `ml/finetune/README.md`.
