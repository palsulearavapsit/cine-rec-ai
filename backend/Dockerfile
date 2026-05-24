# ========================================================
# CINEREC AI BACKEND - DOCKER CONFIGURATION
# Supports both API service and Celery worker runs.
# ========================================================

# Base python runtime stage
FROM python:3.10-slim as base

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

# Install system dependencies (FFmpeg is critical for cutting & compositing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend files and ML folders into image context
COPY . .

# ========================================================
# DEVELOPMENT & PRODUCTION TARGETS
# ========================================================

# Expose ports for FastAPI (8000)
EXPOSE 8000

# Default command: Runs the FastAPI gateway using Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
