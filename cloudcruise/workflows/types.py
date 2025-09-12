from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union


@dataclass
class Workflow:
    id: str
    name: str
    description: Optional[str]
    created_at: str
    updated_at: str
    workspace_id: str
    created_by: str
    enable_popup_handling: bool
    enable_xpath_recovery: bool
    enable_error_code_generation: bool
    enable_service_unavailable_recovery: bool
    enable_action_timing_recovery: bool


WorkflowPropertySchema = Union[str, List[str], Dict[str, Any]]


@dataclass
class WorkflowInputSchema:
    type: Optional[str] = None
    properties: Optional[Dict[str, WorkflowPropertySchema]] = None
    required: Optional[List[str]] = None
    additionalProperties: Optional[bool] = None


@dataclass
class WorkflowMetadata:
    input_schema: WorkflowInputSchema


@dataclass
class InvalidTypeDetail:
    field: str
    expected_display: str
    actual: str


class InputValidationError(Exception):
    def __init__(
        self,
        message: str = "Input validation failed",
        missing_required: Optional[List[str]] = None,
        invalid_types: Optional[List[InvalidTypeDetail]] = None,
        unknown_keys: Optional[List[str]] = None,
    ) -> None:
        super().__init__(message)
        self.missingRequired = missing_required or []
        self.invalidTypes = invalid_types or []
        self.unknownKeys = unknown_keys or []

