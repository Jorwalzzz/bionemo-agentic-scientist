# Production Dockerfile for BioNeMo Agentic Scientist
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies for scientific libraries & RDKit
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install uvicorn fastapi pydantic

# Copy repository code
COPY . .

# Expose Cockpit (8000) and Streamlit (8501)
EXPOSE 8000 8501

# Default: Glassmorphism Web Cockpit
CMD ["python", "serve_cockpit.py"]
