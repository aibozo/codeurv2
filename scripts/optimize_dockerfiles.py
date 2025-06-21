#!/usr/bin/env python3
"""Script to optimize all Dockerfiles with multi-stage builds and caching."""

import os
from pathlib import Path

TEMPLATE_SIMPLE = """# ── Dependencies stage
FROM images/python-poetry-base:3.11 AS deps
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies with cache mount and prefer binary packages
RUN --mount=type=cache,target=/root/.cache/pip \\
    poetry install --no-root --only main --no-interaction --no-ansi --prefer-wheels && \\
    rm -rf /tmp/poetry_cache

# ── Runtime stage
FROM images/python-poetry-base:3.11 AS runtime
WORKDIR /app

# Copy installed dependencies from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy protobuf generated files
COPY apps/*_pb2*.py /app/apps/
COPY apps/__init__.py /app/apps/

# Copy proto definitions and create proto directory with pb2 files
COPY proto /app/proto
RUN mkdir -p /app/proto && cp /app/apps/*_pb2*.py /app/proto/

# Copy app specific files
{app_copies}

ENV PYTHONPATH=/app

{expose}
CMD {cmd}
"""

TEMPLATE_WITH_APT = """# ── Dependencies stage
FROM images/python-poetry-base:3.11 AS deps
WORKDIR /app

# Additional system dependencies
RUN --mount=type=cache,target=/var/cache/apt \\
    apt-get update && apt-get install -y {apt_packages} && \\
    rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies with cache mount and prefer binary packages
RUN --mount=type=cache,target=/root/.cache/pip \\
    poetry install --no-root --only main --no-interaction --no-ansi --prefer-wheels && \\
    rm -rf /tmp/poetry_cache

# ── Runtime stage
FROM images/python-poetry-base:3.11 AS runtime
WORKDIR /app

# Install runtime system dependencies
RUN --mount=type=cache,target=/var/cache/apt \\
    apt-get update && apt-get install -y {apt_packages} && \\
    rm -rf /var/lib/apt/lists/*

# Copy installed dependencies from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy protobuf generated files
COPY apps/*_pb2*.py /app/apps/
COPY apps/__init__.py /app/apps/

# Copy proto definitions and create proto directory with pb2 files
COPY proto /app/proto
RUN mkdir -p /app/proto && cp /app/apps/*_pb2*.py /app/proto/

# Copy app specific files
{app_copies}

ENV PYTHONPATH=/app

{expose}
CMD {cmd}
"""

TEMPLATE_CI = """# ── Dependencies stage
FROM images/python-poetry-base:3.11 AS deps
WORKDIR /app

# Install system dependencies for CI tools
RUN --mount=type=cache,target=/var/cache/apt \\
    apt-get update && apt-get install -y git && \\
    rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies with CI group
RUN --mount=type=cache,target=/root/.cache/pip \\
    poetry install --no-root --with ci --no-interaction --no-ansi --prefer-wheels && \\
    rm -rf /tmp/poetry_cache

# ── Runtime stage
FROM python:3.11 AS runtime
WORKDIR /app

# Install git for CI operations
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

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
"""

# Service configurations
SERVICES = {
    "orchestrator": {
        "template": "simple",
        "app_copies": "COPY apps/orchestrator /app/apps/orchestrator",
        "expose": "EXPOSE 9000 9100",
        "cmd": '["python", "-m", "apps.orchestrator"]'
    },
    "rag_service": {
        "template": "simple",
        "app_copies": "COPY apps/rag_service /app/apps/rag_service",
        "expose": "EXPOSE 8000 9100",
        "cmd": '["python", "-m", "apps.rag_service.main"]'
    },
    "git_adapter": {
        "template": "apt",
        "apt_packages": "libgit2-dev",
        "app_copies": "COPY apps/git_adapter /app/apps/git_adapter",
        "expose": "EXPOSE 8200 8300",
        "cmd": '["python", "-m", "apps.git_adapter.startup"]'
    },
    "symbol_registry": {
        "template": "simple",
        "app_copies": "COPY apps/symbol_registry /app/apps/symbol_registry",
        "expose": "EXPOSE 8080 9090",
        "cmd": '["python", "-m", "apps.symbol_registry.main"]'
    },
    "request_planner": {
        "template": "simple",
        "app_copies": """# Copy orchestrator topics
COPY apps/orchestrator/topics.py /app/apps/orchestrator/topics.py
COPY apps/orchestrator/__init__.py /app/apps/orchestrator/

# Copy agents
COPY apps/agents/__init__.py /app/apps/agents/
COPY apps/agents/request_planner /app/apps/agents/request_planner

# Copy clients
COPY clients /app/clients""",
        "expose": "",
        "cmd": '["python", "-m", "apps.agents.request_planner.agent"]'
    },
    "code_planner": {
        "template": "simple",
        "app_copies": """# Copy orchestrator topics
COPY apps/orchestrator/topics.py /app/apps/orchestrator/topics.py
COPY apps/orchestrator/__init__.py /app/apps/orchestrator/

# Copy agents
COPY apps/agents/__init__.py /app/apps/agents/
COPY apps/agents/code_planner /app/apps/agents/code_planner

# Copy clients
COPY clients /app/clients""",
        "expose": "",
        "cmd": '["python", "-m", "apps.agents.code_planner.agent"]'
    },
    "coding_agent": {
        "template": "apt",
        "apt_packages": "git",
        "app_copies": """# Copy orchestrator topics
COPY apps/orchestrator/topics.py /app/apps/orchestrator/topics.py
COPY apps/orchestrator/__init__.py /app/apps/orchestrator/__init__.py

# Copy agents
COPY apps/agents/__init__.py /app/apps/agents/
COPY apps/agents/coding_agent /app/apps/agents/coding_agent

# Copy clients
COPY clients /app/clients""",
        "expose": "",
        "cmd": '["python", "-m", "apps.agents.coding_agent.agent"]'
    },
    "ci_runner": {
        "template": "ci",
    }
}

def create_optimized_dockerfile(service_name, config):
    """Create an optimized Dockerfile for a service."""
    template_type = config.get("template", "simple")
    
    if template_type == "ci":
        return TEMPLATE_CI
    elif template_type == "apt":
        return TEMPLATE_WITH_APT.format(
            apt_packages=config["apt_packages"],
            app_copies=config["app_copies"],
            expose=config.get("expose", ""),
            cmd=config["cmd"]
        )
    else:
        return TEMPLATE_SIMPLE.format(
            app_copies=config["app_copies"],
            expose=config.get("expose", ""),
            cmd=config["cmd"]
        )

def main():
    """Generate optimized Dockerfiles for all services."""
    root = Path(__file__).parent.parent
    
    for service, config in SERVICES.items():
        if service in ["request_planner", "code_planner", "coding_agent"]:
            dockerfile_path = root / "apps" / "agents" / service / "Dockerfile"
        elif service == "ci_runner":
            dockerfile_path = root / "apps" / service / "Dockerfile"
        else:
            dockerfile_path = root / "apps" / service / "Dockerfile"
            
        optimized_content = create_optimized_dockerfile(service, config)
        
        # Write the optimized version
        optimized_path = dockerfile_path.with_suffix('.Dockerfile.optimized')
        optimized_path.write_text(optimized_content)
        print(f"Created {optimized_path}")

if __name__ == "__main__":
    main()