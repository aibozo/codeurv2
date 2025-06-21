FROM python:3.11

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy poetry files
COPY pyproject.toml poetry.lock* /app/

# Install poetry and export dependencies
RUN pip install poetry && \
    cd /app && poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root --with ci

# Copy protobuf definitions and generated code
COPY proto /app/proto
COPY apps/*_pb2*.py /app/apps/
COPY apps/__init__.py /app/apps/

# Copy orchestrator topics
COPY apps/orchestrator/__init__.py /app/apps/orchestrator/__init__.py
COPY apps/orchestrator/topics.py /app/apps/orchestrator/topics.py

# Copy ci_runner app
COPY apps/ci_runner /app/apps/ci_runner

# Create directories
RUN mkdir -p /artefacts /pipcache

ENV PYTEST_ADDOPTS="-q"
ENV PYTHONPATH=/app

CMD ["python", "-m", "apps.ci_runner.run"]