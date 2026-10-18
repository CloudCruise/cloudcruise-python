from __future__ import annotations

from typing import Any, Dict, Optional

from .types import (
    Workflow,
    WorkflowBranch,
    WorkflowInputSchema,
    WorkflowMetadata,
    WorkflowPropertySchema,
    WorkflowVaultSchemaEntry,
    WorkflowVersion,
    InputValidationError,
    SchemaErrorDetail,
)
def _client():
    # Lazy import to avoid circular imports during package initialization
    from .._default import get_client as _get_client
    return _get_client()

__all__ = [
    "Workflow",
    "WorkflowBranch",
    "WorkflowInputSchema",
    "WorkflowMetadata",
    "WorkflowPropertySchema",
    "WorkflowVaultSchemaEntry",
    "WorkflowVersion",
    "InputValidationError",
    "SchemaErrorDetail",
    # Convenience APIs
    "get_all_workflows",
    "get_workflow_metadata",
    "validate_workflow_input",
    "list_workflow_versions",
    "list_workflow_branches",
]


def get_all_workflows() -> list[Workflow]:
    return _client().workflows.get_all_workflows()


def _selector_kwargs(
    workflow_version: Optional[str], workflow_branch_id: Optional[str]
) -> Dict[str, str]:
    return {
        key: value
        for key, value in (
            ("workflow_version", workflow_version),
            ("workflow_branch_id", workflow_branch_id),
        )
        if value is not None
    }


def get_workflow_metadata(
    workflow_id: str,
    *,
    workflow_version: Optional[str] = None,
    workflow_branch_id: Optional[str] = None,
) -> WorkflowMetadata:
    return _client().workflows.get_workflow_metadata(
        workflow_id, **_selector_kwargs(workflow_version, workflow_branch_id)
    )


def validate_workflow_input(
    workflow_id: str,
    payload: Dict[str, Any],
    *,
    workflow_version: Optional[str] = None,
    workflow_branch_id: Optional[str] = None,
) -> None:
    return _client().workflows.validate_workflow_input(
        workflow_id, payload, **_selector_kwargs(workflow_version, workflow_branch_id)
    )


def list_workflow_versions(workflow_id: str) -> list[WorkflowVersion]:
    return _client().workflows.list_workflow_versions(workflow_id)


def list_workflow_branches(workflow_id: str) -> list[WorkflowBranch]:
    return _client().workflows.list_workflow_branches(workflow_id)
