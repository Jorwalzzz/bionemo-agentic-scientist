FROM python:3.12-slim

# Install system dependencies needed for RDKit / molecular processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxrender1 \
    libxext6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source and assets
COPY . .

# Expose dynamic web port
EXPOSE 8000

# Run FastAPI server via python entrypoint to respect $PORT on Render / Cloud
CMD ["python", "serve_cockpit.py"]
