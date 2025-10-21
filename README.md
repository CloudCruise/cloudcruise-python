# cloudcruise-python

[![MIT License](https://img.shields.io/badge/License-MIT-red.svg?style=flat-square)](LICENSE)
![PyPI - Version](https://img.shields.io/pypi/v/cloudcruise?style=flat-square)
![PyPI - Downloads](https://img.shields.io/pypi/dw/cloudcruise?style=flat-square)
[![GitHub Repo stars](https://img.shields.io/github/stars/CloudCruise/cloudcruise-python?style=flat-square&logo=GitHub&label=cloudcruise-python)](https://github.com/CloudCruise/cloudcruise-python)
[![Discord](https://img.shields.io/discord/1227480834945318933?style=flat-square&logo=Discord&logoColor=white&label=Discord&color=%23434EE4)](https://discord.com/invite/MHjbUqedZF)
[![YC W24](https://img.shields.io/badge/Y%20Combinator-W24-orange?style=flat-square)](https://www.ycombinator.com/companies/cloudcruise)

The official CloudCruise Python SDK for automated browser workflows, encrypted
credential management, realtime run monitoring, and webhook verification.

---

## Installation

```bash
pip install cloudcruise
```

Python 3.10 or newer is required. The package ships with type hints (`py.typed`).

---

## Quick Start

```python
from cloudcruise import CloudCruise, StartRunRequest

client = CloudCruise(
    api_key="<CLOUDCRUISE_API_KEY>",
    encryption_key="<CLOUDCRUISE_ENCRYPTION_KEY>",
)
# Alternatively, set CLOUDCRUISE_API_KEY and CLOUDCRUISE_ENCRYPTION_KEY
# environment variables and instantiate with `client = CloudCruise()`.

run = client.runs.start(
    StartRunRequest(
        workflow_id="105b7ae1-ce62-4a5c-b782-b4b0aec5175a",
        run_input_variables={"email": "test@example.com"},
    )
)

# Listen to specific event types (recommended - clean and type-safe)
run.on("execution.start", lambda e: print(f"Workflow started: {e['payload']['workflow_id']}"))
run.on("execution.step", lambda e: print(f"Step: {e['payload']['current_step']}"))
run.on("execution.success", lambda e: print(f"Success! Output: {e['payload'].get('data')}"))
run.on("end", lambda info: print(f"Run completed: {info['type']}"))

# Or use generic listener for all events (flattened structure)
# run.on("run.event", lambda event: print(f"{event['type']}: {event['payload']}"))

# Block until the run finishes and fetch final results
result = run.wait()
print(result.status, result.data)
```

Environment variables `CLOUDCRUISE_API_KEY`, `CLOUDCRUISE_ENCRYPTION_KEY` are also supported via lazy `cloudcruise.client()`.

---

## Clients

| Client                                   | Description                                            | Module Docs                                        |
| ---------------------------------------- | ------------------------------------------------------ | -------------------------------------------------- |
| [**Vault**](./cloudcruise/vault)         | AES-256-GCM credential storage and retrieval utilities | [`cloudcruise.vault`](./cloudcruise/vault)         |
| [**Workflows**](./cloudcruise/workflows) | Workflow definitions, metadata, and input validation   | [`cloudcruise.workflows`](./cloudcruise/workflows) |
| [**Runs**](./cloudcruise/runs)           | Workflow execution with SSE-based realtime streaming   | [`cloudcruise.runs`](./cloudcruise/runs)           |
| [**Webhook**](./cloudcruise/webhook)     | Webhook payload verification and helpers               | [`cloudcruise.webhook`](./cloudcruise/webhook)     |

All clients are accessible via `CloudCruise` or the convenience `cloudcruise.client()` singleton.

---

## Development

This project uses standard Python tooling with `setuptools`. See
[CONTRIBUTING.md](./CONTRIBUTING.md) for comprehensive instructions.

Quick start:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"  # installs package + dev dependencies

# Run the unit test suite
python -m unittest discover -s tests -p "test_*.py" -v
```

For live staging tests, export `CLOUDCRUISE_API_KEY` and
`CLOUDCRUISE_ENCRYPTION_KEY`, then run `python -m unittest tests/test_live_staging.py -v`.

---

## Documentation & Resources

- [API Documentation](https://docs.cloudcruise.com) – Full platform reference
- [CloudCruise Platform](https://cloudcruise.com) – Product overview
- [Agents & Assistant Context](./AGENTS.md) – How this repository’s automation assistant operates

---

## License

[MIT](LICENSE)
