FROM python:3.11-slim AS loseme-server

WORKDIR /app

RUN apt-get update && \
    apt-get install -y build-essential zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

COPY core/ /core/
RUN pip install --no-cache-dir /core

RUN pip install --no-cache-dir torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu121

RUN pip install --no-cache-dir matplotlib

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/pyproject.toml .

COPY server/api/      api/
COPY server/pipeline/ pipeline/
COPY server/storage/  storage/
COPY server/preview/  preview/
COPY server/wiring.py wiring.py
COPY server/scripts/  scripts/

RUN pip install --no-cache-dir --no-deps .

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
