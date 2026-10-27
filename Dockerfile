# syntax=docker/dockerfile:1
# ==========================================
# Stage 1: Build Frontend SPA
# ==========================================
FROM node:20-slim AS frontend

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
# Cache node_modules across builds — only re-runs npm ci when package-lock.json changes
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Backend Application
# ==========================================
FROM python:3.11-slim AS app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies for OpenCV and InsightFace C++ build
# Cached as a layer — only re-runs if this RUN line changes
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
# --mount=type=cache keeps pip's wheel/download cache on the host permanently.
# Even if requirements.txt changes, already-downloaded packages are NOT re-downloaded.
# This turns the 8–15 min pip install into ~1–2 min on subsequent builds.
COPY backend/requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy backend code
COPY backend/ ./

# Copy built frontend into the expected location
COPY --from=frontend /frontend/dist /frontend/dist

# Create storage and model directories
RUN mkdir -p /app/data /app/models /root/.insightface

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
