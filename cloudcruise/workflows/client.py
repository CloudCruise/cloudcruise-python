from __future__ import annotations

from typing import Any, Dict, List

from .types import (
    Workflow,
    WorkflowMetadata,
    WorkflowInputSchema,
    InputValidationError,
    SchemaErrorDetail,
)
from .validation import validate_input_schema
from ..utils.types import to_dataclass

class WorkflowsClient:
    def __init__(self, make_request) -> None:
        self._make_request = make_request

    def get_all_workflows(self) -> List[Workflow]:
        response = self._make_request("GET", "/workflows")
        return [to_dataclass(item, Workflow) for item in response]

    def get_workflow_metadata(self, workflow_id: str) -> WorkflowMetadata:
        path = f"/workflows/{workflow_id}/metadata"
        response = self._make_request("GET", path)
        if isinstance(response, dict) and "input_schema" not in response:
            nested = response.get("metadata")
            if isinstance(nested, dict) and "input_schema" in nested:
                response = nested
        raw_schema = response.get("input_schema") if isinstance(response, dict) else None
        metadata = to_dataclass(response, WorkflowMetadata)
        if (
            isinstance(raw_schema, dict)
            and isinstance(metadata.input_schema, WorkflowInputSchema)
        ):
            metadata.input_schema._raw_schema = raw_schema
        return metadata

    def validate_workflow_input(self, workflow_id: str, payload: Dict[str, Any]) -> None:
        meta = self.get_workflow_metadata(workflow_id)

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
