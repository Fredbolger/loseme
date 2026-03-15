FROM python:3.11-slim AS loseme-core

WORKDIR /core

COPY pyproject.toml .
COPY loseme_core/ loseme_core/

RUN pip install --no-cache-dir .
