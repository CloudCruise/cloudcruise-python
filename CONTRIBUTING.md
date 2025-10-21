# Contributing to cloudcruise-python

Thank you for your interest in contributing to the CloudCruise Python SDK!
This guide covers everything you need to develop, test, and contribute changes
to the repository.

---

## Project Overview

The SDK provides Pythonic access to the CloudCruise Platform, including:

- **Vault management** – Encrypt, store, and retrieve credentials with
  AES-256-GCM helpers.
- **Workflow execution** – Kick off automated browser workflows via the
  `RunsClient` with realtime SSE streaming.
- **Workflow metadata** – Fetch definitions, input schemas, and proactively
  validate payloads using the `WorkflowsClient`.
- **Webhook verification** – Validate CloudCruise webhook signatures and
  payloads.

The project is organized into modular packages under `cloudcruise/` that map
directly to these capabilities.

---

## Getting Started

### Prerequisites

- Python **3.10+**
- `pip` (or another Python package manager)
- Git
- Recommended: virtual environment tooling (`venv`, `uv`, `conda`, etc.)

### Repository Setup

```bash
git clone https://github.com/CloudCruise/cloudcruise-python.git
cd cloudcruise-python

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install --upgrade pip
pip install -e ".[dev]"  # installs package + dev dependencies (ruff, mypy, etc.)
# Or install without dev dependencies: pip install -e .
```

### Installing Locally in Another Project

To test your cloudcruise-python changes in another project without publishing to
PyPI, install it in editable mode from the local directory:

```bash
# From your other project's directory
cd /path/to/your-other-project
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install cloudcruise in editable mode using the full path
pip install -e /path/to/cloudcruise-python

# Or with dev dependencies
pip install -e "/path/to/cloudcruise-python[dev]"
```

**Editable mode benefits:** Any changes you make to cloudcruise-python code are
immediately reflected in your other project without reinstalling.

Verify the installation:

```bash
python -c "from cloudcruise import CloudCruise; print('Installed successfully!')"
```

### Running Tests

```bash
# Full suite
python -m unittest discover -s tests -p "test_*.py" -v

# Targeted file
python -m unittest tests/test_webhook.py -v

# Live staging (requires CLOUDCRUISE_API_KEY + CLOUDCRUISE_ENCRYPTION_KEY)
python -m unittest tests/test_live_staging.py -v
```

See [tests/README.md](./tests/README.md) for additional tips when running the
live integration tests.

---

## Project Structure

- `cloudcruise/cloudcruise.py` – Core client wiring and HTTP helper.
- `cloudcruise/_default.py` – Lazy global client accessor.
- `cloudcruise/runs/` – Workflow execution APIs and SSE run handles.
- `cloudcruise/vault/` – Encryption utilities and vault client.
- `cloudcruise/workflows/` – Workflow metadata + input validation.
- `cloudcruise/webhook/` – Webhook verification helpers.
- `cloudcruise/utils/` – Shared infrastructure (SSE, events, async queues).
- `tests/` – Unit tests for vault crypto, webhook verification, workflows,
  and optional live staging exercises.

Key components:

- **CloudCruise** – Main entry point that instantiates Vault, Workflows, Runs,
  and Webhook clients.
- **ConnectionManager** – Manages long-lived SSE connections with automatic
  reconnection and fan-out to run subscribers.
- **RunsClient** – Starts and monitors workflow runs; normalizes session IDs
  for streamed events.
- **VaultClient** – Encrypts/decrypts secrets using AES-256-GCM.
- **WorkflowsClient** – Validates run inputs against workflow schemas.

---

## Coding Guidelines

- Follow [PEP 8](https://peps.python.org/pep-0008/) style conventions.
- Use type hints; the package exposes typing info via `py.typed`.
- Favor small, well-documented functions. Add concise comments only when
  behavior might not be obvious.
- Maintain existing error handling patterns—raise descriptive exceptions back
  to the caller.
- Update or add tests for new functionality where practical.

### Linting & Formatting

The repository does not currently ship enforced tooling, but we recommend:

- [`ruff`](https://github.com/astral-sh/ruff) for linting/formatting.
- [`mypy`](http://mypy-lang.org/) for static type checking.

Example:

```bash
pip install ruff mypy
ruff check cloudcruise tests
mypy cloudcruise
```

---

## Development Workflow

1. **Fork and clone** your fork locally.
2. **Create a feature branch**: `git checkout -b feature/your-feature`.
3. **Implement changes**, keeping commits focused and descriptive.
4. **Run tests** (and optional linters) locally.
5. **Update documentation** when you introduce new APIs or behavior.
6. **Commit** using descriptive messages (conventional commits are welcome but
   not required).
7. **Push and open a Pull Request** against `CloudCruise/cloudcruise-python`.

### Pull Request Checklist

- [ ] Tests pass locally (`python -m unittest ...`).
- [ ] Documentation/README updated if applicable.
- [ ] New types or fields include type hints and serialization coverage.
- [ ] No unrelated formatting-only changes.
- [ ] CI (if configured) passes.

Provide a clear summary, link related issues, and call out any manual steps
reviewers should know about.

---

## Publishing (Maintainers)

To cut a new release to PyPI:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"  # includes build and twine

# Update version in pyproject.toml
python -m build            # generates dist/*.tar.gz and dist/*.whl
twine upload dist/*        # use --repository testpypi for dry runs

git tag vX.Y.Z
git push origin main --tags
```

For pre-releases (e.g., `0.0.2a1`), bump the version accordingly in
`pyproject.toml` before building. Consumers can then run
`pip install cloudcruise==0.0.2a1`.

---

## Getting Help

- **Issues:** <https://github.com/CloudCruise/cloudcruise-python/issues>
- **Discord:** <https://discord.com/invite/MHjbUqedZF>
- **API Docs:** <https://docs.cloudcruise.com>

Thanks again for helping improve the CloudCruise Python SDK!
