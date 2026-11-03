"""Refresh tests/contract/api-contract.json from the published CloudCruise API reference.

Only the parts the SDK types mirror are kept, and descriptions, titles and examples are
dropped so wording edits in the docs do not count as contract changes.

    python scripts/sync_api_contract.py          rewrite the snapshot
    python scripts/sync_api_contract.py --check  exit 1 if the published API differs from the snapshot

Needs PyYAML (``pip install -e '.[dev]'``).
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

import yaml

SOURCE = "https://docs.cloudcruise.com/run-api/run-api.yaml"
SNAPSHOT = Path(__file__).resolve().parent.parent / "tests" / "contract" / "api-contract.json"
RESPOND_PATH = "/run/{session_id}/decision/respond"
DROPPED_KEYS = {"description", "title", "example", "summary"}


def strip(node: Any) -> Any:
    if isinstance(node, list):
        return [strip(item) for item in node]
    if isinstance(node, dict):
        return {key: strip(value) for key, value in node.items() if key not in DROPPED_KEYS}
    return node


def extract(spec: dict[str, Any]) -> dict[str, Any]:
    schemas = spec["components"]["schemas"]
    return {
        "source": SOURCE,
        "paths": sorted(spec["paths"]),
        "webhooks": sorted(spec.get("webhooks") or {}),
        "subscribable_events": sorted(
            schemas["RunSpecificWebhook"]["properties"]["event_types_subscribed"]["items"]["enum"]
        ),
        "decision_requested": strip(schemas["AgentDecisionRequestedEvent"]),
        "decision_answered": strip(schemas["AgentDecisionAnsweredEvent"]),
        "decision_respond_request": strip(
            spec["paths"][RESPOND_PATH]["post"]["requestBody"]["content"]["application/json"]["schema"]
        ),
    }


def main() -> int:
    with urllib.request.urlopen(SOURCE, timeout=30) as response:
        spec = yaml.safe_load(response.read())
    rendered = json.dumps(extract(spec), indent=2) + "\n"
    if "--check" in sys.argv[1:]:
        if SNAPSHOT.read_text() != rendered:
            print(
                f"FAIL: {SOURCE} no longer matches tests/contract/api-contract.json. "
                "Run python scripts/sync_api_contract.py, then fix the types until the tests pass.",
                file=sys.stderr,
            )
            return 1
        print("OK: the published API matches the SDK contract snapshot")
        return 0
    SNAPSHOT.write_text(rendered)
    print(f"Wrote {SNAPSHOT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
