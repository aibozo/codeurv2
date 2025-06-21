FROM python:3.11-slim
WORKDIR /app

# Copy poetry files
COPY pyproject.toml poetry.lock* /app/
RUN pip install --no-cache-dir poetry && \
    cd /app && poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# Copy protobuf files
COPY proto /app/proto
COPY apps/*_pb2*.py /app/apps/
COPY apps/__init__.py /app/apps/

# Copy orchestrator topics
COPY apps/orchestrator/topics.py /app/apps/orchestrator/topics.py
COPY apps/orchestrator/__init__.py /app/apps/orchestrator/

# Copy agents
COPY apps/agents/__init__.py /app/apps/agents/
COPY apps/agents/request_planner /app/apps/agents/request_planner

# Copy clients
COPY clients /app/clients

ENV PYTHONPATH=/app

CMD ["python", "-m", "apps.agents.request_planner.agent"]