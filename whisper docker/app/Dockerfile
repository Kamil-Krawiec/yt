FROM python:3.11-slim

# Install ffmpeg (needed for audio/video processing)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install faster-whisper
RUN pip install --no-cache-dir faster-whisper

WORKDIR /app
COPY transcribe.py .

# Default env (can be overridden in docker-compose)
ENV MODEL_SIZE=base LANGUAGE=pl

CMD ["python", "transcribe.py"]
