FROM python:3.11-slim AS loseme-client

WORKDIR /app

RUN apt-get update && \
    apt-get install -y build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install loseme-core
COPY --from=loseme-core:latest /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Install client dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy client source
COPY extractors/ extractors/
COPY sources/    sources/
COPY ingest/     ingest/
COPY cli/        cli/
COPY web/        web/
COPY preview/ preview/

ENV PYTHONPATH=/app

EXPOSE 3000
CMD ["uvicorn", "web.main:app", "--host", "0.0.0.0", "--port", "3000"]
