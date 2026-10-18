from __future__ import annotations

import unittest
from typing import Any
from unittest.mock import patch

import cloudcruise.workflows as workflows_module
from cloudcruise import (
    InputValidationError,
    WorkflowBranch,
    WorkflowMetadata,
    WorkflowVersion,
)
from cloudcruise.workflows.client import WorkflowsClient

_LATEST_METADATA = {
    "input_schema": {
        "type": "object",
        "properties": {"added_in_latest": {"type": "string"}},
        "required": ["added_in_latest"],
    },
    "workspace_id": "ws-1",
    "vault_schema": {},
    "version_id": "version-latest",
    "version": "2.0.0",
    "branch_id": "branch-main",
}

_PINNED_METADATA = {
    "input_schema": {
        "type": "object",
        "properties": {"field_of_1_x": {"type": "string"}},
        "required": ["field_of_1_x"],
    },
    "workspace_id": "ws-1",
    "vault_schema": {},
    "version_id": "version-1-2-3",
    "version": "1.2.3",
    "branch_id": "branch-main",
}


class _RecordingApi:
    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.requests: list[tuple[str, str]] = []

    def __call__(self, method: str, path: str, body: Any = None) -> Any:
        self.requests.append((method, path))
        return self.responses[path]


class TestWorkflowMetadataVersionSelection(unittest.TestCase):
    def test_metadata_without_a_selector_requests_the_unchanged_path(self) -> None:
        """Existing callers must keep hitting exactly the URL they always did, so
        their behaviour and any request mocking they rely on stay the same."""
        api = _RecordingApi({"/workflows/wf-1/metadata": _LATEST_METADATA})

        metadata = WorkflowsClient(api).get_workflow_metadata("wf-1")

        self.assertEqual(api.requests, [("GET", "/workflows/wf-1/metadata")])
        self.assertEqual(metadata.version, "2.0.0")

    def test_metadata_with_a_version_range_sends_it_as_the_version_query(self) -> None:
        """The SDK names the selector workflow_version, as on runs.start(); the API
        takes it as the version query parameter, URL-encoded since ranges contain
        characters like ^ and spaces."""
        api = _RecordingApi({"/workflows/wf-1/metadata?version=%5E1.2.0": _PINNED_METADATA})

        metadata = WorkflowsClient(api).get_workflow_metadata("wf-1", workflow_version="^1.2.0")

        self.assertEqual(metadata.version_id, "version-1-2-3")
        self.assertEqual(metadata.version, "1.2.3")
        self.assertIn("field_of_1_x", metadata.input_schema.properties)

    def test_metadata_with_a_branch_sends_it_as_the_branch_id_query(self) -> None:
        """workflow_branch_id maps to the API's branch_id query parameter, the same
        name GET /workflows/{id} uses for branch reads."""
        api = _RecordingApi({"/workflows/wf-1/metadata?branch_id=branch-feature": _PINNED_METADATA})

        WorkflowsClient(api).get_workflow_metadata("wf-1", workflow_branch_id="branch-feature")

        self.assertEqual(api.requests, [("GET", "/workflows/wf-1/metadata?branch_id=branch-feature")])

    def test_metadata_with_both_selectors_raises_before_any_request(self) -> None:
        """A version and a branch can point at different versions, and the API rejects
        the combination; failing locally names the problem and skips the request."""
        api = _RecordingApi({})

        with self.assertRaises(ValueError):
            WorkflowsClient(api).get_workflow_metadata(
                "wf-1", workflow_version="1.2.3", workflow_branch_id="branch-feature"
            )

        self.assertEqual(api.requests, [])

    def test_metadata_with_a_selector_fails_against_an_api_that_ignores_it(self) -> None:
        """An API without version selection ignores the unknown query parameter and
        describes the default branch instead. Its response has no version_id, and
        returning it would silently hand back the wrong version's schema."""
        old_api_response = {key: _LATEST_METADATA[key] for key in ("input_schema", "workspace_id", "vault_schema")}
        api = _RecordingApi({"/workflows/wf-1/metadata?version=1.2.3": old_api_response})

        with self.assertRaisesRegex(RuntimeError, "does not support selecting a workflow version"):
            WorkflowsClient(api).get_workflow_metadata("wf-1", workflow_version="1.2.3")


    def test_metadata_with_a_selector_accepts_the_wrapped_response_shape(self) -> None:
        """The client already unwraps {"metadata": {...}} responses; a selected read in
        that shape carries version_id inside the wrapper and must not be mistaken for an
        API that ignored the selector."""
        api = _RecordingApi({"/workflows/wf-1/metadata?version=1.2.3": {"metadata": _PINNED_METADATA}})

        metadata = WorkflowsClient(api).get_workflow_metadata("wf-1", workflow_version="1.2.3")

        self.assertEqual(metadata.version_id, "version-1-2-3")


class TestModuleLevelConvenienceFunctions(unittest.TestCase):
    def test_module_functions_pass_selectors_and_list_through_the_default_client(self) -> None:
        """cloudcruise.workflows' convenience functions use the shared default client;
        they must offer the same selectors and list methods as WorkflowsClient, or
        callers of that API can't use them."""
        api = _RecordingApi({
            "/workflows/wf-1/metadata?branch_id=branch-feature": _PINNED_METADATA,
            "/workflows/wf-1/versions": [],
            "/workflows/wf-1/branches": [],
        })

        class _DefaultClient:
            workflows = WorkflowsClient(api)

        with patch("cloudcruise._default.get_client", return_value=_DefaultClient()):
            workflows_module.validate_workflow_input(
                "wf-1", {"field_of_1_x": "x"}, workflow_branch_id="branch-feature"
            )
            self.assertEqual(workflows_module.list_workflow_versions("wf-1"), [])
            self.assertEqual(workflows_module.list_workflow_branches("wf-1"), [])

        self.assertEqual(api.requests, [
            ("GET", "/workflows/wf-1/metadata?branch_id=branch-feature"),
            ("GET", "/workflows/wf-1/versions"),
            ("GET", "/workflows/wf-1/branches"),
        ])


class TestValidateWorkflowInputVersionSelection(unittest.TestCase):
    def test_validation_with_a_version_uses_that_versions_schema(self) -> None:
        """A payload built for an older release must pass against that release's
        schema even though the latest version requires a different field."""
        api = _RecordingApi({
            "/workflows/wf-1/metadata": _LATEST_METADATA,
            "/workflows/wf-1/metadata?version=1.2.3": _PINNED_METADATA,
        })
        client = WorkflowsClient(api)

        client.validate_workflow_input("wf-1", {"field_of_1_x": "x"}, workflow_version="1.2.3")
        with self.assertRaises(InputValidationError):
            client.validate_workflow_input("wf-1", {"field_of_1_x": "x"})

    def test_validation_without_a_selector_still_works_with_a_one_argument_metadata_override(self) -> None:
        """Callers may subclass WorkflowsClient and override get_workflow_metadata with
        the original one-argument signature; unpinned validation must keep calling it
        that way."""

        class _OneArgumentOverride(WorkflowsClient):
            def get_workflow_metadata(self, workflow_id: str) -> WorkflowMetadata:  # type: ignore[override]
                return WorkflowsClient(_RecordingApi({"/workflows/wf-1/metadata": _LATEST_METADATA})).get_workflow_metadata(workflow_id)

        _OneArgumentOverride(_RecordingApi({})).validate_workflow_input("wf-1", {"added_in_latest": "x"})


class TestListVersionsAndBranches(unittest.TestCase):
    def test_list_workflow_versions_returns_versions_with_their_branch(self) -> None:
        """Each version names its branch so callers can pick a release on a given
        branch and pass its version as workflow_version."""
        api = _RecordingApi({
            "/workflows/wf-1/versions": [
                {
                    "version_id": "v-2",
                    "version": "2.0.0",
                    "branch_id": "branch-main",
                    "version_note": "Adds a field",
                    "created_by": "user-1",
                    "created_at": "2026-10-16T00:00:00Z",
                },
            ]
        })

        versions = WorkflowsClient(api).list_workflow_versions("wf-1")

        self.assertEqual(versions, [
            WorkflowVersion(
                version_id="v-2",
                version="2.0.0",
                created_at="2026-10-16T00:00:00Z",
                branch_id="branch-main",
                version_note="Adds a field",
                created_by="user-1",
            )
        ])

    def test_list_workflow_versions_tolerates_an_api_without_branch_ids(self) -> None:
        """APIs older than branch support list versions without branch_id; the list
        must still parse, with branch_id left as None."""
        api = _RecordingApi({
            "/workflows/wf-1/versions": [
                {"version_id": "v-1", "version": "1.0.0", "version_note": None, "created_by": None, "created_at": "t"},
            ]
        })

        versions = WorkflowsClient(api).list_workflow_versions("wf-1")

        self.assertIsNone(versions[0].branch_id)

    def test_list_workflow_branches_marks_the_default_branch(self) -> None:
        """is_default tells callers which branch unpinned runs use; extra fields the
        API returns, such as effectiveProtection, are ignored."""
        api = _RecordingApi({
            "/workflows/wf-1/branches": [
                {
                    "id": "branch-main",
                    "workflow_id": "wf-1",
                    "workspace_id": "ws-1",
                    "name": "main",
                    "head_version_id": "v-2",
                    "is_default": True,
                    "created_by": "user-1",
                    "created_at": "t0",
                    "updated_at": "t1",
                    "effectiveProtection": {"protected": False},
                },
                {
                    "id": "branch-feature",
                    "workflow_id": "wf-1",
                    "workspace_id": "ws-1",
                    "name": "feature",
                    "head_version_id": "v-3",
                    "is_default": False,
                    "created_by": "user-1",
                    "created_at": "t2",
                    "updated_at": "t3",
                },
            ]
        })

        branches = WorkflowsClient(api).list_workflow_branches("wf-1")

        self.assertEqual([(b.name, b.is_default) for b in branches], [("main", True), ("feature", False)])
        self.assertIsInstance(branches[0], WorkflowBranch)


if __name__ == "__main__":
    unittest.main()
