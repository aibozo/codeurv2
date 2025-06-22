FROM python:3.11-slim

# Install common system dependencies needed by most services
RUN apt-get update && apt-get install -y \
    git \
    libpq-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install poetry and configure it to not create virtualenvs
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry config installer.modern-installation true && \
    poetry config installer.parallel true

# Configure pip to prefer binary packages
RUN pip config set global.prefer-binary true

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_CACHE_DIR=/tmp/poetry_cache
ENV PIP_PREFER_BINARY=1