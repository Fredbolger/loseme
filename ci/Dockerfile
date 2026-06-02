FROM python:3.11-slim

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

# Heavy dependencies installed ONCE
RUN pip install \
    fastapi \
    "uvicorn[standard]" \
    "pydantic>=2.0" \
    httpx \
    qdrant-client \
    sentence-transformers \
    pypdf \
    beautifulsoup4 \
    lxml \
    typer \
    pytest \
    pytest-cov \
    pyflakes

WORKDIR /workspace
