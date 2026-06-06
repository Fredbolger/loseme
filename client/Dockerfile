FROM python:3.11-slim AS loseme-client

WORKDIR /app

RUN apt-get update && \
    apt-get install -y build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY core/ /core/
RUN pip install --no-cache-dir /core

COPY client/pyproject.toml .
RUN pip install --no-cache-dir --no-build-isolation .

COPY client/extractors/ extractors/
COPY client/sources/    sources/
COPY client/ingest/     ingest/
COPY client/cli/        cli/
COPY client/web/        web/
COPY client/preview/    preview/
COPY client/pyproject.toml .

ENV PYTHONPATH=/app
EXPOSE 3000
CMD ["uvicorn", "web.main:app", "--host", "0.0.0.0", "--port", "3000"]
