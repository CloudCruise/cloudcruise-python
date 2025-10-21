from __future__ import annotations

from typing import Any, Dict

from .types import (
    Workflow,
    WorkflowInputSchema,
    WorkflowMetadata,
    WorkflowPropertySchema,
    InputValidationError,
)
def _client():
    # Lazy import to avoid circular imports during package initialization
    from .._default import get_client as _get_client
    return _get_client()

__all__ = [
    "Workflow",
    "WorkflowInputSchema",
    "WorkflowMetadata",
    "WorkflowPropertySchema",
    "InputValidationError",
    # Convenience APIs
    "get_all_workflows",
    "get_workflow_metadata",
    "validate_workflow_input",
]


def get_all_workflows() -> list[Workflow]:
    return _client().workflows.get_all_workflows()


def get_workflow_metadata(workflow_id: str) -> WorkflowMetadata:
    return _client().workflows.get_workflow_metadata(workflow_id)


def validate_workflow_input(workflow_id: str, payload: Dict[str, Any]) -> None:
    return _client().workflows.validate_workflow_input(workflow_id, payload)
