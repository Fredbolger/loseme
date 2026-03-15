FROM python:3.11-slim AS loseme-server

WORKDIR /app

# System dependencies needed for building some ML packages
RUN apt-get update && \
    apt-get install -y build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install loseme-core first
COPY --from=loseme-core:latest /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Install PyTorch (swap cu121 for cpu if no GPU)
RUN pip install --no-cache-dir torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu121

# Install server dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy server source
COPY api/      api/
COPY pipeline/ pipeline/
COPY storage/  storage/
COPY preview/  preview/
COPY wiring.py wiring.py

ENV PYTHONPATH=/app

EXPOSE 8000
CMD ["uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
