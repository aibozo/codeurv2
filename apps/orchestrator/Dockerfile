FROM python:3.11-slim
WORKDIR /app

# Copy poetry files
COPY pyproject.toml poetry.lock* /app/
RUN pip install --no-cache-dir poetry && \
    cd /app && poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# Copy protobuf generated files
COPY apps/*_pb2*.py /app/apps/
COPY apps/__init__.py /app/apps/

# Copy proto definitions
COPY proto /app/proto

# Copy orchestrator app
COPY apps/orchestrator /app/apps/orchestrator

ENV PYTHONPATH=/app

CMD ["python", "-m", "apps.orchestrator"]