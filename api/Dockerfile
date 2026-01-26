FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && \
    apt-get install -y build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . /app

RUN pip install --upgrade pip wheel setuptools

RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
#RUN pip install torch torchvision torchaudio \
#    --index-url https://download.pytorch.org/whl/cu121

RUN pip install "transformers>=4.41" "tokenizers>=0.15"

RUN pip install "FlagEmbedding==1.3.2"


# Python dependencies (API runtime)
RUN pip install \
    fastapi \
    uvicorn \
    pydantic \
    pytest \
    pytest-mock \
    httpx \
    typer \
    qdrant-client>=1.7.0\
    sentence-transformers>=2.6\
    einops \
    pypdf\
    bs4

# 🔑 Ensure consistent imports everywhere
ENV PYTHONPATH=/app

EXPOSE 8000
