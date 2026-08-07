from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Union


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
    _raw_schema: Optional[Dict[str, Any]] = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )


@dataclass
class WorkflowVaultSchemaEntry:
    type: Optional[Literal["credential"]] = None
    domain: Optional[str] = None
    example: Optional[str] = None


@dataclass
class WorkflowMetadata:
    input_schema: WorkflowInputSchema
    workspace_id: Optional[str] = None
    vault_schema: Dict[str, WorkflowVaultSchemaEntry] = field(default_factory=dict)


@dataclass
class InvalidTypeDetail:
    field: str
    expected_display: str
    actual: str


@dataclass
class SchemaErrorDetail:
    instancePath: str
    schemaPath: str
    keyword: str
    message: str


class InputValidationError(Exception):
    def __init__(
        self,
        message: str = "Input validation failed",
        missing_required: Optional[List[str]] = None,
        invalid_types: Optional[List[InvalidTypeDetail]] = None,
        unknown_keys: Optional[List[str]] = None,
        schema_errors: Optional[List[SchemaErrorDetail]] = None,
    ) -> None:
        super().__init__(message)
        self.missingRequired = missing_required or []
        self.invalidTypes = invalid_types or []
        self.unknownKeys = unknown_keys or []
        self.schemaErrors = schema_errors or []

