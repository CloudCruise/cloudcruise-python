from __future__ import annotations

from typing import Any, Dict, List

from .types import (
    Workflow,
    WorkflowMetadata,
    WorkflowInputSchema,
    WorkflowPropertySchema,
    InputValidationError,
    InvalidTypeDetail,
)

class WorkflowsClient:
    def __init__(self, make_request) -> None:
        self._make_request = make_request

    def get_all_workflows(self) -> List[Workflow]:
        return self._make_request("GET", "/workflows")

    def get_workflow_metadata(self, workflow_id: str) -> WorkflowMetadata:
        path = f"/workflows/{workflow_id}/metadata"
        return self._make_request("GET", path)

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

        if isinstance(raw_schema, dict):
            properties = raw_schema.get("properties") or {}
            required = raw_schema.get("required") or []
            disallow_extras = (raw_schema.get("additionalProperties") is False)
        else:
            schema: WorkflowInputSchema = raw_schema or WorkflowInputSchema()
            properties = schema.properties or {}
            required = schema.required or []
            disallow_extras = (schema.additionalProperties is False)

        missing_required = [k for k in required if k not in payload]

        def detect_type(v: Any) -> str:
            if v is None:
                return "null"
            if isinstance(v, list):
                return "array"
            if isinstance(v, bool):
                return "boolean"
            if isinstance(v, int) and not isinstance(v, bool):
                return "integer"
            if isinstance(v, float):
                return "number"
            if isinstance(v, dict):
                return "object"
            return "string" if isinstance(v, str) else type(v).__name__

        def expected_types_of(defn: WorkflowPropertySchema) -> List[str]:
            if defn is None:
                return []
            raw = defn
            if isinstance(defn, dict):
                raw = defn.get("type")  # type: ignore
            if raw is None:
                return []
            arr = raw if isinstance(raw, list) else [raw]
            allowed = {"array", "boolean", "integer", "number", "object", "string", "null"}
            out: List[str] = []
            for t in arr:  # type: ignore
                if isinstance(t, str):
                    t = t.lower()
                    if t in allowed:
                        out.append(t)
            return out

        def matches(expected: List[str], actual: str) -> bool:
            if not expected:
                return True
            if actual in expected:
                return True
            if actual == "integer" and "number" in expected:
                return True
            return False

        invalid_types: List[InvalidTypeDetail] = []
        for key, schema_def in properties.items():
            if key not in payload:
                continue
            exp = expected_types_of(schema_def)
            act = detect_type(payload.get(key))
            if not matches(exp, act):
                invalid_types.append(InvalidTypeDetail(field=key, expected_display=" | ".join(exp or ["any"]), actual=act))

        unknown_keys: List[str] = []
        if disallow_extras:
            unknown_keys = [k for k in payload.keys() if k not in properties]

        if missing_required or invalid_types or unknown_keys:
            parts: List[str] = []
            if missing_required:
                parts.append(f"missing required: {', '.join(missing_required)}")
            if invalid_types:
                parts.append("; ".join([f"{e.field}: expected {e.expected_display}, got {e.actual}" for e in invalid_types]))
            if unknown_keys:
                parts.append(f"unknown keys: {', '.join(unknown_keys)}")
            msg = f"Workflow input validation failed: {' | '.join(parts)}"
            raise InputValidationError(msg, missing_required, invalid_types, unknown_keys)
