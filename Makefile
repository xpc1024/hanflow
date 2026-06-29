.PHONY: install test test-unit lint typecheck ci

install:
	uv sync --all-extras

test:
	uv run pytest

test-unit:
	uv run pytest tests/ -m "not integration"

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy hanflow

ci: lint typecheck test
