# Repository Guidelines

## Project Structure & Module Organization

- `cloudcruise/`: core package. Subpackages: `workflows/`, `runs/`, `vault/`, `webhook/`, `utils/` (common files: `client.py`, `types.py`, `utils.py`).
- Entry points: `cloudcruise/cloudcruise.py` (main client), `cloudcruise/_default.py` (shared default client), `cloudcruise/py.typed` (PEP 561 marker).
- `tests/`: unittest suite. `tests/.env` holds local config for optional live tests.
- `pyproject.toml`: setuptools build metadata (Python 3.10+).

## Build, Test, and Development

- Setup (inside a venv): `pip install -e .` • Live tests: `pip install python-dotenv`.
- Run all tests: `python -m unittest discover -s tests -p 'test_*.py' -v`.
- Run a specific test: `python -m unittest tests/test_webhook.py -v` or `python -m unittest tests.test_webhook.TestWebhook.test_verify_signature_ok -v`.
- Build sdist/wheel: `python -m pip install build && python -m build`.

## Coding Style & Naming Conventions

- Follow PEP 8 with 4‑space indents and explicit type hints; keep `from __future__ import annotations` at the top of new modules.
- Data models use `@dataclass`; prefer `TypedDict` for typed payloads; keep network code in `client.py` and helpers in `utils/`.
- Naming: modules `lowercase_underscores.py`; classes `CamelCase`; functions/methods `snake_case`.
- Public API: when adding exports, update `cloudcruise/__init__.py` (`__all__` and re-exports) to maintain discoverability.

## Testing Guidelines

- Framework: `unittest`. Tests live in `tests/` and are named `test_*.py`; classes `Test*`, methods `test_*`.
- Unit tests must not hit the network. Integration/live checks belong in `tests/test_live_staging.py` and are skipped by default.
- Live test config: set `CLOUDCRUISE_API_KEY` and `CLOUDCRUISE_ENCRYPTION_KEY` (or use `tests/.env`).

## Commit & Pull Request Guidelines

- Commits observed in history are short, imperative, and lowercase (e.g., `remove debug logs`, `improve typed suggestions`); no trailing punctuation.
- PRs must include: clear description, rationale, any API changes, tests for new behavior, and updated docs where applicable. Link issues and ensure `python -m unittest` passes.

## Security & Configuration

- Never commit real secrets. Use env vars: `CLOUDCRUISE_API_KEY` and `CLOUDCRUISE_ENCRYPTION_KEY`.
- `tests/.env` is for local development only; prefer ephemeral keys for manual tests.
