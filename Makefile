.PHONY: install test test-unit test-cov lint typecheck ci

install:
	uv sync --all-extras

test:
	uv run pytest

test-unit:
	uv run pytest tests/ -m "not integration"

test-cov:
	uv run pytest --cov=hanflow --cov-report=term-missing --cov-report=html
	@echo "HTML report: htmlcov/index.html"

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy hanflow

ci: lint typecheck test
