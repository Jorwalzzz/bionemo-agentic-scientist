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

# Run FastAPI server with proxy headers enabled for Cloudflare / Render edge
CMD ["uvicorn", "serve_cockpit:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
