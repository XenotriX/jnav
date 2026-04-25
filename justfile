test TEST="":
    uv run pytest --no-header {{TEST}}
coverage:
    uv run pytest --cov --cov-report=term:skip-covered --cov-report=html
format:
    uv run ruff format
check:
    uv run lefthook run pre-commit --all-files --force
