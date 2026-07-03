FROM python:3.11-slim

WORKDIR /app

# Install compilation essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source files
COPY . .

# Ensure necessary audio directories exist
RUN mkdir -p static/audio_cache

# Expose default container port
EXPOSE 8000

# Start command (binds to the port environment variable defined by host)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
