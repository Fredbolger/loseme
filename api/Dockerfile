FROM python:3.11-slim

WORKDIR /app

COPY . /app 

# Install make and other build tools
RUN apt-get update && \
    apt-get install -y build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install fastapi uvicorn pydantic pytest pytest-mock sphinx sphinx_rtd_theme myst-parser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

