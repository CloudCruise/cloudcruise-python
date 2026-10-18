from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from .types import (
    Workflow,
    WorkflowBranch,
    WorkflowMetadata,
    WorkflowInputSchema,
    WorkflowVersion,
    InputValidationError,
    SchemaErrorDetail,
)
from .validation import validate_input_schema
from ..utils.types import to_dataclass


def _version_selector(
    workflow_version: Optional[str], workflow_branch_id: Optional[str]
) -> Dict[str, str]:
    selector = {
        key: value
        for key, value in (
            ("workflow_version", workflow_version),
            ("workflow_branch_id", workflow_branch_id),
        )
        if value is not None
    }
    if len(selector) > 1:
        raise ValueError("At most one of workflow_version, workflow_branch_id may be set")
    return selector

class WorkflowsClient:
    def __init__(self, make_request) -> None:
        self._make_request = make_request

    def get_all_workflows(self) -> List[Workflow]:
        response = self._make_request("GET", "/workflows")
        return [to_dataclass(item, Workflow) for item in response]

    def get_workflow_metadata(
        self,
        workflow_id: str,
        *,
        workflow_version: Optional[str] = None,
        workflow_branch_id: Optional[str] = None,
    ) -> WorkflowMetadata:
        """Describe the input and vault schemas of one workflow version.

        Without a selector this is the latest version on the default branch.
        ``workflow_version`` (exact version or semver range) or
        ``workflow_branch_id`` select the same version a run started with that
        pin would execute; at most one may be set.
        """
        selector = _version_selector(workflow_version, workflow_branch_id)
        query = {
            ("version" if key == "workflow_version" else "branch_id"): value
            for key, value in selector.items()
        }
        path = f"/workflows/{workflow_id}/metadata"
        if query:
            path = f"{path}?{urlencode(query)}"
        response = self._make_request("GET", path)
        if isinstance(response, dict) and "input_schema" not in response:
            nested = response.get("metadata")
            if isinstance(nested, dict) and "input_schema" in nested:
                response = nested
        if selector and isinstance(response, dict) and "version_id" not in response:
            raise RuntimeError(
                "This CloudCruise API does not support selecting a workflow version or branch "
                "for metadata yet; its response describes the default branch instead"
            )
        raw_schema = response.get("input_schema") if isinstance(response, dict) else None
        metadata = to_dataclass(response, WorkflowMetadata)
        if (
            isinstance(raw_schema, dict)
            and isinstance(metadata.input_schema, WorkflowInputSchema)
        ):
            metadata.input_schema._raw_schema = raw_schema
        return metadata

    def list_workflow_versions(self, workflow_id: str) -> List[WorkflowVersion]:
        """List every version of a workflow across all branches, newest first."""
        response = self._make_request("GET", f"/workflows/{workflow_id}/versions")
        return [to_dataclass(item, WorkflowVersion) for item in response]

    def list_workflow_branches(self, workflow_id: str) -> List[WorkflowBranch]:
        """List a workflow's branches, oldest first; ``is_default`` marks the default branch."""
        response = self._make_request("GET", f"/workflows/{workflow_id}/branches")
        return [to_dataclass(item, WorkflowBranch) for item in response]

    def validate_workflow_input(
        self,
        workflow_id: str,
        payload: Dict[str, Any],
        *,
        workflow_version: Optional[str] = None,
        workflow_branch_id: Optional[str] = None,
    ) -> None:
        """Check a payload against a workflow version's input schema.

        Takes the same optional version or branch selector as
        ``get_workflow_metadata``. Raises ``InputValidationError`` if invalid.
        """
        selector = _version_selector(workflow_version, workflow_branch_id)
        meta = self.get_workflow_metadata(workflow_id, **selector)

        raw_schema: Any = None
        if isinstance(meta, dict):
            if "input_schema" in meta:
                raw_schema = meta.get("input_schema")
            else:
                m = meta.get("metadata") if isinstance(meta.get("metadata"), dict) else None
                if isinstance(m, dict):
                    raw_schema = m.get("input_schema")
        else:
            try:
                raw_schema = getattr(meta, "input_schema", None)
            except Exception:
                raw_schema = None

        if isinstance(raw_schema, WorkflowInputSchema):
            schema = raw_schema._raw_schema
            if schema is None:
                schema = {
                    key: value
                    for key, value in {
                        "type": raw_schema.type,
                        "properties": raw_schema.properties,
                        "required": raw_schema.required,
                        "additionalProperties": raw_schema.additionalProperties,
                    }.items()
                    if value is not None
                }
        elif isinstance(raw_schema, dict):
            schema = raw_schema
        elif raw_schema is None:
            schema = {}
        else:
            detail = SchemaErrorDetail(
                instancePath="",
                schemaPath="#",
                keyword="schema",
                message="input schema must be an object",
            )
            raise InputValidationError(
                f"Workflow input schema is invalid: {detail.message}",
                schema_errors=[detail],
            )

        validate_input_schema(schema, payload)
