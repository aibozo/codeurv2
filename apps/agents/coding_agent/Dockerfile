FROM python:3.11-slim

# Install git and other build dependencies
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock* /app/

# Install poetry and dependencies
RUN pip install poetry && \
    cd /app && poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# Copy protobuf files
COPY proto /app/proto
COPY apps/*_pb2*.py /app/apps/
COPY apps/__init__.py /app/apps/

# Copy orchestrator topics
COPY apps/orchestrator/topics.py /app/apps/orchestrator/topics.py
COPY apps/orchestrator/__init__.py /app/apps/orchestrator/__init__.py

# Copy agents
COPY apps/agents/__init__.py /app/apps/agents/
COPY apps/agents/coding_agent /app/apps/agents/coding_agent

# Copy clients
COPY clients /app/clients

# Set PYTHONPATH
ENV PYTHONPATH=/app

CMD ["python", "-m", "apps.agents.coding_agent.agent"]