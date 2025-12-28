FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && \
    apt-get install -y build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . /app

# Python dependencies (API runtime)
RUN pip install \
    fastapi \
    uvicorn \
    pydantic \
    pytest \
    pytest-mock \
    httpx

# 🔑 Ensure consistent imports everywhere
ENV PYTHONPATH=/app

EXPOSE 8000

