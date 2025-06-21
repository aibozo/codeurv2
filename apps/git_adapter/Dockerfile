FROM python:3.11-slim
RUN apt-get update && apt-get install -y git libgit2-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# Copy poetry files
COPY pyproject.toml poetry.lock* /app/
RUN pip install --no-cache-dir poetry && cd /app && poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root

# Copy protobuf files
COPY proto /app/proto
COPY apps/*_pb2*.py /app/apps/
COPY apps/__init__.py /app/apps/

# Copy git_adapter app
COPY apps/git_adapter /app/apps/git_adapter

# Copy protobuf Python files to proto directory  
RUN mkdir -p /app/proto && cp /app/apps/*_pb2*.py /app/proto/

ENV PYTHONPATH=/app

EXPOSE 8200 8300
CMD ["python", "-m", "apps.git_adapter.startup"]