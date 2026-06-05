FROM python:3.13-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

# Export locked deps to requirements.txt, then pip-install system-wide (no venv in a container)
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && \
    uv export --no-dev --frozen --no-hashes -o /tmp/requirements.txt && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Download Piper voice model — en_US-lessac-medium (~60 MB)
RUN mkdir -p tts/models && \
    curl -fsSL -o tts/models/en_US-lessac-medium.onnx \
      "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" && \
    curl -fsSL -o tts/models/en_US-lessac-medium.onnx.json \
      "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"

# Pre-download Whisper base model (~150 MB) — cached in image, no runtime download needed
ENV HF_HOME=/app/.cache/huggingface
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"

# Copy application source last to maximize cache hits on the layers above
COPY . .

# OpenShift runs pods as an arbitrary UID in group 0 — make everything group-writable
RUN chown -R 1001:0 /app && chmod -R g=u /app

EXPOSE 8000
USER 1001
CMD ["chainlit", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]
