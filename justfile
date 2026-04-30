set shell := ["bash", "-c"]

# List all available recipes
help:
    @just --list

# Install dependencies and setup environment (installs uv, lefthook, and bun if missing)
init:
    @echo "Checking for uv..."
    @if ! command -v uv > /dev/null; then \
        echo "uv not found. Installing uv..."; \
        curl -LsSf https://astral.sh/uv/install.sh | sh; \
    else \
        echo "uv is already installed."; \
    fi

    @echo "Checking for lefthook..."
    @if ! command -v lefthook > /dev/null; then \
        echo "lefthook not found. Installing lefthook via uv tool..."; \
        uv tool install lefthook; \
    else \
        echo "lefthook is already installed."; \
    fi

    @echo "Setting up lefthook hooks..."
    @lefthook install
    @echo "Installing dependencies..."
    @just sync

# Install CLI and Server in editable mode
install:
    @echo "Installing openopc-cli and openopc-server in editable mode..."
    uv tool install --editable .

# Sync all dependencies in the workspace
sync:
    @echo "Syncing all workspace dependencies..."
    uv sync

check:
    uv run ruff format .
    uv run ruff check . --fix
    uv run mypy .
    uv run pytest -ra -q

# Run pre-commit checks using lefthook
pre-commit:
    @echo "Running pre-commit hooks..."
    @lefthook run pre-commit
    @echo "Pre-commit hooks passed!"

# Clean all temporary files and caches across the workspace
clean:
    @echo "Cleaning workspace..."
    rm -rf .venv .ruff_cache .mypy_cache .pytest_cache .coverage dist
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    @for member in apps/server apps/cli packages/shared; do \
        if [ -d "$member" ]; then \
            echo "Cleaning $member..."; \
            rm -rf "$member"/.ruff_cache "$member"/.mypy_cache "$member"/.pytest_cache "$member"/.coverage "$member"/dist; \
        fi \
    done
