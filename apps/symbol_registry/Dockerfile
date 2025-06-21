FROM python:3.11-slim
WORKDIR /app

# Copy poetry files from root
COPY pyproject.toml poetry.lock* /app/
RUN pip install --no-cache-dir poetry && cd /app && poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root

# Copy protobuf generated files
COPY apps/*_pb2*.py /app/apps/
COPY apps/__init__.py /app/apps/

# Copy proto definitions
COPY proto /app/proto

# Copy symbol_registry app
COPY apps/symbol_registry /app/apps/symbol_registry

ENV PYTHONPATH=/app

CMD ["python", "-m", "apps.symbol_registry.main"]