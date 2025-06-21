FROM python:3.11-slim
WORKDIR /app

# Copy poetry files
COPY pyproject.toml poetry.lock* /app/
RUN pip install --no-cache-dir poetry && \
    cd /app && poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# Copy protobuf definitions and generated files
COPY proto /app/proto
COPY apps/*_pb2*.py /app/apps/
COPY apps/__init__.py /app/apps/

# Copy rag_service app
COPY apps/rag_service /app/apps/rag_service

# Copy protobuf Python files to proto directory
RUN mkdir -p /app/proto && cp /app/apps/*_pb2*.py /app/proto/

ENV PYTHONPATH=/app

EXPOSE 8000 9100
CMD ["python", "-m", "apps.rag_service.main"]