"""End-to-end live test for the CloudCruise Python SDK.

Exercises the happy path across the three main namespaces:

    1. ``workflows.get_workflow_metadata`` — surface the expected input schema.
    2. ``vault.create`` — create a dummy credential for a demo domain.
    3. ``runs.start`` + ``wait`` — trigger a workflow run and stream SSE events
       until it terminates.
    4. ``vault.delete`` — clean up the credential (unless ``SKIP_CLEANUP`` is
       set).

Usage
-----

::

    CLOUDCRUISE_API_KEY=... CLOUDCRUISE_ENCRYPTION_KEY=... \
        python scripts/live_e2e.py

Environment variables
---------------------

Required:
    CLOUDCRUISE_API_KEY        Your workspace API key.
    CLOUDCRUISE_ENCRYPTION_KEY 32-byte hex encoding of your encryption key.

Optional:
    CLOUDCRUISE_BASE_URL  Defaults to https://api.cloudcruise.com.
    WORKFLOW_ID           Defaults to the demo workflow below.
    VAULT_DOMAIN          Defaults to https://demo.cloudcruise.com.
    PERMISSIONED_USER_ID  Defaults to a timestamped random id so repeated
                          runs don't collide.
    RUN_INPUT_JSON        JSON object passed as ``run_input_variables``.
                          Defaults to ``{}``. If the workflow requires
                          specific inputs, override this (e.g.
                          ``RUN_INPUT_JSON='{"permissioned_user_id":"u1"}'``).
    SKIP_CLEANUP          If set, the vault entry is kept after the run.

Exits 0 on ``execution.success``, 2 on any other terminal status, and 1 on
setup / fatal errors.
"""

from __future__ import annotations

import json
import hashlib
import hmac
import os
import random
import string
import sys
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_REPO_ROOT / "tests" / ".env")
except ImportError:
    pass

from cloudcruise import (
    CloudCruise,
    CloudCruiseParams,
    FlattenedRunEvent,
    RunResult,
    StartRunRequest,
    VaultEntryInput,
    WebhookPayload,
    WorkflowMetadata,
)
from cloudcruise.webhook import verify_signature


DEFAULT_WORKFLOW_ID = "85c2e6b4-313a-4a97-836f-2128467eb504"
DEFAULT_VAULT_DOMAIN = "https://demo.cloudcruise.com"


def _rand_suffix(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def _log(section: str, body: str = "") -> None:
    banner = f"\n==== {section} ===="
    print(banner + (f"\n{body}" if body else ""), flush=True)


def _fmt(obj: Any) -> str:
    if is_dataclass(obj):
        obj = asdict(obj)
    try:
        return json.dumps(obj, indent=2, default=str, sort_keys=True)
    except Exception:
        return repr(obj)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _sign_webhook_body(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _check_webhook_dataclass() -> None:
    secret = "sdk-live-e2e-secret"
    body = json.dumps(
        {
            "event": "execution.success",
            "expires_at": int(time.time()) + 60,
            "payload": {"ok": True},
        },
        separators=(",", ":"),
    ).encode("utf-8")

    verified = verify_signature(body, _sign_webhook_body(body, secret), secret)
    _assert(
        isinstance(verified, WebhookPayload),
        f"verify_signature returned {type(verified).__name__}, expected WebhookPayload",
    )
    _assert(verified.event == "execution.success", "webhook event did not round-trip")
    _assert(verified.data["payload"]["ok"] is True, "webhook extra payload missing")


def main() -> int:
    api_key = os.environ.get("CLOUDCRUISE_API_KEY")
    encryption_key = os.environ.get("CLOUDCRUISE_ENCRYPTION_KEY")
    base_url = os.environ.get("CLOUDCRUISE_BASE_URL") or "https://api.cloudcruise.com"

    if not api_key or not encryption_key:
        print(
            "Missing CLOUDCRUISE_API_KEY or CLOUDCRUISE_ENCRYPTION_KEY. "
            "Export them, or put them in tests/.env.",
            file=sys.stderr,
        )
        return 1

    workflow_id = os.environ.get("WORKFLOW_ID") or DEFAULT_WORKFLOW_ID
    vault_domain = os.environ.get("VAULT_DOMAIN") or DEFAULT_VAULT_DOMAIN
    permissioned_user_id = (
        os.environ.get("PERMISSIONED_USER_ID")
        or f"sdk-e2e-{int(time.time())}-{_rand_suffix()}"
    )

    run_input_raw = os.environ.get("RUN_INPUT_JSON") or "{}"
    try:
        run_input: Dict[str, Any] = json.loads(run_input_raw)
    except json.JSONDecodeError as exc:
        print(f"RUN_INPUT_JSON is not valid JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(run_input, dict):
        print("RUN_INPUT_JSON must be a JSON object.", file=sys.stderr)
        return 1

    skip_cleanup = bool(os.environ.get("SKIP_CLEANUP"))

    client = CloudCruise(
        CloudCruiseParams(
            api_key=api_key,
            encryption_key=encryption_key,
            base_url=base_url,
        )
    )

    _log(
        "Configuration",
        _fmt(
            {
                "base_url": base_url,
                "workflow_id": workflow_id,
                "vault_domain": vault_domain,
                "permissioned_user_id": permissioned_user_id,
                "run_input": run_input,
                "skip_cleanup": skip_cleanup,
            }
        ),
    )

    _log("Step 1: fetch workflow metadata")
    try:
        metadata = client.workflows.get_workflow_metadata(workflow_id)
        _assert(
            isinstance(metadata, WorkflowMetadata),
            f"metadata is {type(metadata).__name__}, expected WorkflowMetadata",
        )
        print(_fmt(metadata))
    except Exception as exc:
        print(f"Failed to fetch workflow metadata: {exc!r}", file=sys.stderr)
        return 1

    _log("Step 1b: verify SDK dataclass helpers")
    try:
        workflows = client.workflows.get_all_workflows()
        _assert(isinstance(workflows, list), "get_all_workflows did not return a list")
        if workflows:
            _assert(
                hasattr(workflows[0], "id"),
                "get_all_workflows returned items without attribute access",
            )
            print(f"first workflow id = {workflows[0].id}")
        _check_webhook_dataclass()
        print("webhook verification returned WebhookPayload")
    except Exception as exc:
        print(f"SDK dataclass helper check failed: {exc!r}", file=sys.stderr)
        return 1

    # If the workflow has a ``credentials`` required input that resolves to
    # the demo vault domain, wire it to the vault entry we are about to
    # create so the demo workflow runs out of the box. The caller can still
    # override via ``RUN_INPUT_JSON``.
    input_schema = metadata.input_schema
    required_inputs = set(input_schema.required or [])
    if "credentials" in required_inputs and "credentials" not in run_input:
        run_input["credentials"] = permissioned_user_id
        print(
            f"\nauto-filled run_input['credentials'] = {permissioned_user_id!r} "
            "(workflow requires it)"
        )

    _log(f"Step 2: create vault entry for {vault_domain}")
    alias = f"sdk-e2e-{_rand_suffix()}"
    try:
        vault_entry = client.vault.create(
            VaultEntryInput(
                domain=vault_domain,
                permissioned_user_id=permissioned_user_id,
                user_name="demo_user",
                password="demo_password",
                user_alias=alias,
            )
        )
    except Exception as exc:
        print(f"Failed to create vault entry: {exc!r}", file=sys.stderr)
        return 1

    vault_id = vault_entry.id
    print(_fmt(vault_entry))
    if not vault_id:
        print("Warning: vault response did not include an id", file=sys.stderr)

    exit_code = 1
    try:
        _log(f"Step 3: start run for workflow {workflow_id}")
        handle = client.runs.start(
            StartRunRequest(
                workflow_id=workflow_id,
                run_input_variables=run_input,
            )
        )
        print(f"session_id = {handle.sessionId}")
        saw_run_event_dataclass = False

        def on_event(evt: FlattenedRunEvent) -> None:
            nonlocal saw_run_event_dataclass
            _assert(
                isinstance(evt, FlattenedRunEvent),
                f"run.event callback received {type(evt).__name__}, expected FlattenedRunEvent",
            )
            saw_run_event_dataclass = True
            payload = evt.payload or {}
            # Keep output manageable: print the event type and a short summary.
            summary_keys = ("current_step", "next_step", "status", "message")
            summary = {k: payload.get(k) for k in summary_keys if k in payload}
            tail = f" {summary}" if summary else ""
            print(f"[event] {evt.type}{tail}", flush=True)

        handle.on("run.event", on_event)
        handle.on("error", lambda err: print(f"[error] {err!r}", flush=True))
        handle.on("end", lambda evt: print(f"[end] {evt}", flush=True))

        _log("Step 4: waiting for run to end (may take a while)")
        result = handle.wait()
        _assert(
            isinstance(result, RunResult),
            f"handle.wait returned {type(result).__name__}, expected RunResult",
        )
        _assert(saw_run_event_dataclass, "did not receive any FlattenedRunEvent callbacks")

        direct_result = client.runs.get_results(handle.sessionId)
        _assert(
            isinstance(direct_result, RunResult),
            f"runs.get_results returned {type(direct_result).__name__}, expected RunResult",
        )
        _assert(
            direct_result.session_id == result.session_id,
            "direct get_results session_id did not match wait result",
        )

        _log("Final result", _fmt(result))

        status = result.status or "unknown"
        errors = result.errors or []
        print(f"\nstatus:     {status}")
        print(f"errors:     {len(errors)}")
        print(f"workflow:   {result.workflow_id}")
        print(f"session:    {result.session_id}")

        exit_code = 0 if status == "execution.success" else 2
        return exit_code
    except Exception as exc:
        print(f"Run failed: {exc!r}", file=sys.stderr)
        return 1
    finally:
        if skip_cleanup:
            _log("Step 5: skipping vault cleanup (SKIP_CLEANUP set)")
        else:
            _log(f"Step 5: delete vault entry for {vault_domain}")
            try:
                client.vault.delete(
                    {
                        "domain": vault_domain,
                        "permissioned_user_id": permissioned_user_id,
                    }
                )
                print("vault entry deleted")
            except Exception as exc:
                print(f"cleanup failed: {exc!r}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
