"""Install the latest CloudCruise SDK from PyPI and run a live smoke test.

The script creates a temporary virtualenv, installs ``cloudcruise`` from PyPI,
then runs this flow using the installed package:

    1. Create a vault entry.
    2. Fetch the vault entry back from the API.
    3. Start a workflow run using that vault entry's permissioned user id.
    4. Wait for and print the final run result.

Required environment variables:
    CLOUDCRUISE_API_KEY
    CLOUDCRUISE_ENCRYPTION_KEY
    WORKFLOW_ID

Optional environment variables:
    CLOUDCRUISE_BASE_URL       Defaults to https://api.cloudcruise.com.
    VAULT_DOMAIN               Defaults to https://demo.cloudcruise.com.
    PERMISSIONED_USER_ID       Defaults to a unique test id.
    VAULT_INPUT_KEY            Defaults to credentials.
    RUN_INPUT_JSON             Extra JSON object merged into run_input_variables.
    SKIP_CLEANUP               Keep the vault entry if set.

Example:
    CLOUDCRUISE_API_KEY=... CLOUDCRUISE_ENCRYPTION_KEY=... WORKFLOW_ID=... \
        python scripts/live_pypi_e2e.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import venv
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / "tests" / ".env"


CHILD_SCRIPT = r'''
from __future__ import annotations

import json
import os
import random
import string
import sys
import time
from dataclasses import asdict, is_dataclass
from typing import Any

from cloudcruise import (
    CloudCruise,
    CloudCruiseParams,
    FlattenedRunEvent,
    GetVaultEntriesFilters,
    StartRunRequest,
    VaultEntryInput,
)


def log(title: str, body: Any | None = None) -> None:
    print(f"\n==== {title} ====", flush=True)
    if body is not None:
        print(fmt(body), flush=True)


def fmt(value: Any) -> str:
    if is_dataclass(value):
        value = asdict(value)
    try:
        return json.dumps(value, indent=2, sort_keys=True, default=str)
    except TypeError:
        return repr(value)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def random_suffix(length: int = 8) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def main() -> int:
    api_key = require_env("CLOUDCRUISE_API_KEY")
    encryption_key = require_env("CLOUDCRUISE_ENCRYPTION_KEY")
    workflow_id = require_env("WORKFLOW_ID")

    base_url = os.environ.get("CLOUDCRUISE_BASE_URL") or "https://api.cloudcruise.com"
    vault_domain = os.environ.get("VAULT_DOMAIN") or "https://demo.cloudcruise.com"
    permissioned_user_id = (
        os.environ.get("PERMISSIONED_USER_ID")
        or f"pypi-sdk-e2e-{int(time.time())}-{random_suffix()}"
    )
    vault_input_key = os.environ.get("VAULT_INPUT_KEY") or "credentials"
    skip_cleanup = bool(os.environ.get("SKIP_CLEANUP"))

    try:
        run_input = json.loads(os.environ.get("RUN_INPUT_JSON") or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"RUN_INPUT_JSON is not valid JSON: {exc}") from exc
    if not isinstance(run_input, dict):
        raise RuntimeError("RUN_INPUT_JSON must be a JSON object")
    run_input.setdefault(vault_input_key, permissioned_user_id)

    client = CloudCruise(
        CloudCruiseParams(
            api_key=api_key,
            encryption_key=encryption_key,
            base_url=base_url,
        )
    )

    log(
        "Configuration",
        {
            "base_url": base_url,
            "workflow_id": workflow_id,
            "vault_domain": vault_domain,
            "permissioned_user_id": permissioned_user_id,
            "run_input": run_input,
            "skip_cleanup": skip_cleanup,
        },
    )

    log("Create vault entry")
    vault_entry = client.vault.create(
        VaultEntryInput(
            domain=vault_domain,
            permissioned_user_id=permissioned_user_id,
            user_name="cloudcruise_sdk_test_user",
            password=f"cloudcruise-sdk-test-{random_suffix(16)}",
            user_alias=f"pypi-sdk-e2e-{random_suffix()}",
        )
    )
    print(fmt(vault_entry), flush=True)

    try:
        log("Fetch vault entry")
        matches = client.vault.get(
            GetVaultEntriesFilters(
                domain=vault_domain,
                permissioned_user_id=permissioned_user_id,
            )
        )
        print(fmt(matches), flush=True)
        if len(matches) != 1:
            raise RuntimeError(f"Expected 1 fetched vault entry, got {len(matches)}")
        fetched = matches[0]
        if fetched.permissioned_user_id != permissioned_user_id:
            raise RuntimeError("Fetched vault entry does not match the created entry")

        log("Start workflow run")
        handle = client.runs.start(
            StartRunRequest(
                workflow_id=workflow_id,
                run_input_variables=run_input,
            )
        )
        print(f"session_id = {handle.sessionId}", flush=True)

        def on_event(event: FlattenedRunEvent) -> None:
            payload = event.payload or {}
            summary = {
                key: payload.get(key)
                for key in ("status", "message", "current_step", "next_step")
                if key in payload
            }
            print(f"[event] {event.type} {summary}".rstrip(), flush=True)

        handle.on("run.event", on_event)
        handle.on("error", lambda err: print(f"[error] {err!r}", flush=True))

        log("Await run result")
        result = handle.wait()
        log("Run result", result)

        if result.status != "execution.success":
            return 2
        return 0
    finally:
        if skip_cleanup:
            log("Skipping cleanup")
        else:
            log("Delete vault entry")
            client.vault.delete(
                {
                    "domain": vault_domain,
                    "permissioned_user_id": permissioned_user_id,
                }
            )
            print("vault entry deleted", flush=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
'''


def load_dotenv(path: Path) -> None:
    """Load simple KEY=VALUE lines without requiring python-dotenv."""
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print(f"+ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def main() -> int:
    load_dotenv(ENV_FILE)

    missing = [
        name
        for name in ("CLOUDCRUISE_API_KEY", "CLOUDCRUISE_ENCRYPTION_KEY", "WORKFLOW_ID")
        if not os.environ.get(name)
    ]
    if missing:
        print(f"Missing required environment variable(s): {', '.join(missing)}", file=sys.stderr)
        print("Set them in your shell or in tests/.env.", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="cloudcruise-pypi-e2e-") as tmp:
        tmp_path = Path(tmp)
        venv_path = tmp_path / ".venv"
        print(f"Creating temporary virtualenv at {venv_path}", flush=True)
        venv.EnvBuilder(with_pip=True, clear=True).create(venv_path)

        python = venv_path / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        run([str(python), "-m", "pip", "install", "--upgrade", "pip"], cwd=tmp_path)
        run([str(python), "-m", "pip", "install", "--upgrade", "cloudcruise"], cwd=tmp_path)
        run([str(python), "-m", "pip", "show", "cloudcruise"], cwd=tmp_path)
        run([str(python), "-c", textwrap.dedent(CHILD_SCRIPT)], cwd=tmp_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
