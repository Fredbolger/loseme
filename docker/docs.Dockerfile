# Dockerfile.docs
FROM python:3.11-slim

# Set working directory for the whole container
WORKDIR /app

# Install build tools and make
RUN apt-get update && \
    apt-get install -y make && \
    rm -rf /var/lib/apt/lists/*

# Copy the project files
COPY . /app

# Install Python dependencies for Sphinx
RUN pip install \
    sphinx \
    sphinx_rtd_theme \
    myst-parser \
    pydantic \
    fastapi

# Default command: clean and build HTML in docs/
CMD ["sh", "-c", "make -C docs clean html"]

