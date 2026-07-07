FROM python:3.12-slim AS base
WORKDIR /app
RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY hanflow/ ./hanflow/
COPY workflows/ ./workflows/

ENV HANFLOW__WORKSPACE_ROOT=/workspace
ENV HANFLOW__DB_URL=postgresql://hanflow:hanflow@postgres:5432/hanflow
ENV HANFLOW_API_KEY=${HANFLOW_API_KEY:-}
ENV HANFLOW_SERVER__INLINE_WORKER=true

EXPOSE 8000
CMD ["uv", "run", "hanflow", "serve", "--host", "0.0.0.0", "--port", "8000"]
