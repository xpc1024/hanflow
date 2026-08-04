.PHONY: install test test-unit test-docker test-cov lint typecheck ci

install:
	uv sync --all-extras

test:
	uv run pytest

test-unit:
	uv run pytest tests/ -m "not integration"

# Real-daemon docker container tests only (the 4 lifecycle tests in
# tests/isolation/test_docker_provisioner.py). Skipped locally when no
# docker daemon / python:3.11-slim image is present; run in CI on every
# push. -v lists each test name so the skip/run status is visible.
test-docker:
	uv run pytest -m docker -v

# On-demand coverage report. Branch coverage and omit policy come from
# [tool.coverage.*] in pyproject.toml. Not part of `ci` (no fail-under gate).
test-cov:
	uv run pytest --cov=hanflow --cov-report=term-missing --cov-report=html
	@echo "HTML report: htmlcov/index.html"

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy hanflow

ci: lint typecheck test
