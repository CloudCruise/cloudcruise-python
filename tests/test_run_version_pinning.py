from __future__ import annotations

import unittest
from collections.abc import Callable
from typing import Any
from unittest.mock import patch

from cloudcruise import CloudCruise, CloudCruiseParams, InputValidationError
from cloudcruise.runs.client import RunsClient
from cloudcruise.runs.types import StartRunRequest


class _FakeSubscription:
    def on(self, event: str, listener: Callable[..., Any]) -> None:
        pass

    def off(self, event: str, listener: Callable[..., Any]) -> None:
        pass

    def close(self) -> None:
        pass


class _FakeConnectionManager:
    def ensure_client_id(self) -> str:
        return "client-1"

    def connect_if_needed(self) -> None:
        pass

    def subscribe(self, session_id: str) -> _FakeSubscription:
        return _FakeSubscription()


class _LatestVersionWorkflows:
    """Stands in for WorkflowsClient, whose validate_workflow_input checks against
    the default branch's latest version. It rejects every payload so a test fails
    if start() still consults it."""

    def __init__(self) -> None:
        self.validated: list[str] = []

    def validate_workflow_input(self, workflow_id: str, payload: dict[str, Any]) -> None:
        self.validated.append(workflow_id)
        raise InputValidationError("missing required field 'added_in_latest'")


class _ErrorResponse:
    ok = False
    status_code = 400
    reason = "Bad Request"
    text = "validation failed"
    headers = {"content-type": "application/json"}

    def __init__(self, body: dict[str, Any]) -> None:
        self._body = body

    def json(self) -> dict[str, Any]:
        return self._body


class TestRunVersionPinning(unittest.TestCase):
    def setUp(self) -> None:
        self.posted_payloads: list[dict[str, Any] | None] = []

        def make_request(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
            self.posted_payloads.append(body)
            return {"session_id": "session-1"}

        self.workflows = _LatestVersionWorkflows()
        self.client = RunsClient(_FakeConnectionManager(), make_request, self.workflows)  # type: ignore[arg-type]

    def test_dataclass_request_sends_workflow_version_range_when_set(self) -> None:
        """A semver range on the request must reach POST /run unchanged; the backend
        resolves it to the highest matching tagged release."""
        self.client.start(
            StartRunRequest(workflow_id="wf-1", run_input_variables={}, workflow_version="^1.2.0")
        )

        self.assertEqual(self.posted_payloads[0]["workflow_version"], "^1.2.0")
        self.assertNotIn("workflow_branch_id", self.posted_payloads[0])

    def test_dict_request_sends_workflow_branch_id_when_set(self) -> None:
        """Dict requests are passed through as-is, so a branch pin given as a dict key
        must reach POST /run just like the dataclass field does."""
        self.client.start(
            {"workflow_id": "wf-1", "run_input_variables": {}, "workflow_branch_id": "branch-uuid"}
        )

        self.assertEqual(self.posted_payloads[0]["workflow_branch_id"], "branch-uuid")
        self.assertNotIn("workflow_version", self.posted_payloads[0])

    def test_dataclass_request_without_pins_omits_both_pin_keys_from_payload(self) -> None:
        """asdict() serializes every field, including None ones. Backends without run
        version pinning reject unknown fields even when null, so unset pins must be
        dropped or every unpinned run would fail against them."""
        self.client.start(StartRunRequest(workflow_id="wf-1", run_input_variables={}))

        self.assertNotIn("workflow_version", self.posted_payloads[0])
        self.assertNotIn("workflow_branch_id", self.posted_payloads[0])

    def test_dict_request_with_explicit_none_pins_omits_both_pin_keys_from_payload(self) -> None:
        """A dict caller may set the pin keys to None explicitly; those must be dropped
        for the same reason as unset dataclass fields."""
        self.client.start(
            {
                "workflow_id": "wf-1",
                "run_input_variables": {},
                "workflow_version": None,
                "workflow_branch_id": None,
            }
        )

        self.assertNotIn("workflow_version", self.posted_payloads[0])
        self.assertNotIn("workflow_branch_id", self.posted_payloads[0])

    def test_unpinned_request_keeps_serializing_other_none_fields_as_before(self) -> None:
        """Only the pin keys are dropped; existing None-valued fields keep being sent so
        the payload for an unpinned run is unchanged from earlier SDK versions."""
        self.client.start(StartRunRequest(workflow_id="wf-1", run_input_variables={}))

        self.assertIn("dry_run", self.posted_payloads[0])
        self.assertIsNone(self.posted_payloads[0]["dry_run"])

    def test_setting_both_version_and_branch_pins_raises_before_any_request(self) -> None:
        """The backend accepts at most one pin and answers 400 otherwise; failing locally
        gives a clearer error and avoids a pointless request."""
        with self.assertRaises(ValueError):
            self.client.start(
                StartRunRequest(
                    workflow_id="wf-1",
                    run_input_variables={},
                    workflow_version="1.2.3",
                    workflow_branch_id="branch-uuid",
                )
            )
        with self.assertRaises(ValueError):
            self.client.start(
                {
                    "workflow_id": "wf-1",
                    "run_input_variables": {},
                    "workflow_version": "1.x",
                    "workflow_branch_id": "branch-uuid",
                }
            )

        self.assertEqual(self.posted_payloads, [])

    def test_pinned_run_is_not_validated_against_the_latest_versions_schema(self) -> None:
        """An older release may take different inputs than the default branch's latest
        version, which is the only schema the workflows client can fetch. The run must
        go straight to POST /run so the server validates it against the pinned version."""
        self.client.start(
            StartRunRequest(
                workflow_id="wf-1",
                run_input_variables={"field_of_1_x": "value"},
                workflow_version="1.2.3",
            )
        )

        self.assertEqual(self.workflows.validated, [])
        self.assertEqual(self.posted_payloads[0]["run_input_variables"], {"field_of_1_x": "value"})

    def test_unpinned_run_does_not_fetch_metadata_before_posting(self) -> None:
        """The server validates every run against the version that runs, so a local
        check before POST /run would only cost an extra request per run."""
        self.client.start({"workflow_id": "wf-1", "run_input_variables": {"name": "x"}})

        self.assertEqual(self.workflows.validated, [])
        self.assertEqual(len(self.posted_payloads), 1)

    def test_server_validation_rejection_raises_input_validation_error_from_start(self) -> None:
        """With no local check, a 400 from POST /run is how callers learn their input is
        invalid; it must surface from start() as InputValidationError with its field
        details, as the local check did."""
        cloudcruise = CloudCruise(CloudCruiseParams(api_key="test-key", encryption_key="00" * 32))
        client = RunsClient(_FakeConnectionManager(), cloudcruise._make_request)  # type: ignore[arg-type]
        response = _ErrorResponse({
            "message": "Validation failed for run_input_variables",
            "run_input_variables_errors": [
                {
                    "field": "#/required",
                    "message": "must have required property 'name'",
                    "keyword": "required",
                    "expected": {"missingProperty": "name"},
                    "received": None,
                },
            ],
            "input_schema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        })

        with (
            patch("cloudcruise.cloudcruise.requests.request", return_value=response),
            self.assertRaises(InputValidationError) as caught,
        ):
            client.start(
                StartRunRequest(workflow_id="wf-1", run_input_variables={}, workflow_version="1.2.3")
            )

        self.assertEqual(caught.exception.missingRequired, ["name"])


if __name__ == "__main__":
    unittest.main()
