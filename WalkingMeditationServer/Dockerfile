# Walking Meditation Server — shared dev/runtime image
# Python 3.13 is required by the app (see READList/Python_Version.md).
FROM python:3.13-slim-bookworm

# System deps:
#   ffmpeg     -> _ensure_ffmpeg() at startup + wav->mp3 conversion
#   libsndfile -> soundfile / librosa
#   sox        -> sox python bindings
#   git, curl  -> huggingface_hub downloads
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libsndfile1 \
        sox \
        git \
        curl \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    # Keep the Hugging Face model cache on a volume so the Qwen3-TTS weights
    # survive rebuilds and are not re-downloaded by every teammate on every build.
    HF_HOME=/opt/hf-cache

WORKDIR /app

# Install the CPU-only build of torch first. The default PyPI wheels for
# linux/amd64 are the CUDA ones (~2.5GB); pinning the CPU index keeps the image
# small and identical for Mac (arm64) and Windows/Linux (amd64) teammates.
# For GPU machines, see the note in DOCKER.md.
RUN pip install --index-url https://download.pytorch.org/whl/cpu \
        torch==2.10.0 torchaudio==2.10.0

# Requirements are copied on their own so dependency layers cache across
# ordinary source edits.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

# 0.0.0.0, not the 127.0.0.1 in main.py's __main__ block — otherwise the port
# is unreachable from outside the container.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
