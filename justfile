test:
    uv run pytest --cov --cov-report=term:skip-covered --cov-report=html
format:
    uv run ruff format
