# ============================================================
# AI Rental Decision Intelligence Platform — Backend Dockerfile
# Multi-stage build: smaller final image, faster rebuilds via layer caching
# ============================================================

FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files & buffering stdout (cleaner container logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps needed to build psycopg2, xgboost, lightgbm wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (separate layer) so `docker build` only
# re-installs packages when requirements.txt actually changes.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Now copy the actual application code
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
