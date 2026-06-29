FROM python:3.11-slim AS builder
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY hanflow ./hanflow
RUN uv sync --frozen --no-dev

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/hanflow /app/hanflow
ENV PATH="/app/.venv/bin:$PATH"
ENV HANFLOW_INLINE_WORKER=true
EXPOSE 8000
CMD ["hanflow", "serve", "--host", "0.0.0.0", "--port", "8000"]
