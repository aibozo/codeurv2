# Testing Guide

## Quick Start

To run tests with real OpenAI API (using gpt-4.1-nano for minimal cost):

1. Set your OpenAI API key:
   ```bash
   export OPENAI_API_KEY=your-api-key-here
   ```

2. Run the test setup script:
   ```bash
   ./scripts/setup_test_env.sh
   ```

3. Run tests:
   ```bash
   poetry run pytest
   ```

## Test Modes

### 1. Full Integration Tests (with OpenAI nano)
Uses real OpenAI API with gpt-4.1-nano model:
```bash
export OPENAI_API_KEY=your-key
export LLM_BACKEND=openai
export PLANNER_MODEL=gpt-4.1-nano
export CODING_MODEL=gpt-4.1-nano
export EMBEDDING_BACKEND=openai
export EMBEDDING_MODEL=text-embedding-3-small
poetry run pytest
```

### 2. Mock Mode (no external services)
For CI or offline testing:
```bash
export LLM_BACKEND=dummy
export MOCK_LLM=1
export MOCK_EMBEDDING=1
poetry run pytest --ignore=apps/rag_service/tests --ignore=apps/symbol_registry/tests
```

### 3. Dummy Provider Tests
Tests using the dummy LLM provider:
```bash
export LLM_BACKEND=dummy
poetry run pytest clients/llm_client/tests
```

## Required Services

For full integration tests, you need:
- PostgreSQL (for Symbol Registry)
- Qdrant (for RAG service)

The setup script will start these automatically using Docker.

## Cost Estimates

Using gpt-4.1-nano:
- Input: $0.15 per 1M tokens
- Output: $0.60 per 1M tokens
- Embeddings (text-embedding-3-small): $0.02 per 1M tokens

Typical test suite run: < $0.01