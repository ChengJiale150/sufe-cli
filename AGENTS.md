## Project

### Structure



### Submodules



## Development

### Environment

- Use `uv` for Python environment and dependency management.
- Run Python with `uv run`; do not use `python` or `python3`.
- Add dependencies with `uv add <package>`; do not edit `pyproject.toml` directly.

### Source Code Style

- Use strict type hints compatible with `mypy --strict`.
- Use modern Python syntax such as `str | None` and `list[str]`.
- Use Pydantic for validation and configuration schemas where applicable.