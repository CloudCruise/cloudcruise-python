from __future__ import annotations

from typing import Any, Dict, Generic, List, Literal, TypeVar, TypedDict, Union

# Re-use EventType from runs.types to avoid circular imports
# We'll import it later after updating runs/types.py

# Event Payload TypedDicts
class ExecutionQueuedPayload(TypedDict):
    session_id: str
    workflow_id: str


class ExecutionStartPayload(TypedDict, total=False):
    session_id: str
    workflow_id: str
    live_view_url: str  # optional


class ExecutionStepPayload(TypedDict):
    session_id: str
    workflow_id: str
    current_step: str
    next_step: str


class InteractionWaitingPayload(TypedDict):
    session_id: str
    workflow_id: str
    current_step: str
    missing_properties: List[str]
    expected_json_schema_datamodel: Dict[str, Any]
    message: str


# InteractionFinishedPayload has two possible shapes
class InteractionFinishedPayloadVariant1(TypedDict):
    session_id: str
    workflow_id: str
    current_step: str
    missing_properties: List[str]  # empty list in this variant
    expected_json_schema_datamodel: Dict[str, Any]
    message: str


class InteractionFinishedPayloadVariant2(TypedDict, total=False):
    session_id: str
    workflow_id: str
    provided_input: Any
    message: str  # optional
    expected_json_schema_datamodel: Dict[str, Any]


InteractionFinishedPayload = Union[
    InteractionFinishedPayloadVariant1,
    InteractionFinishedPayloadVariant2
]


class AgentErrorAnalysisPayload(TypedDict, total=False):
    analysis_step_name: str
    ai_analysis: str  # optional
    root_cause_analysis: str  # optional
    error_category: str  # optional


class ExecutionRequeuedPayload(TypedDict, total=False):
    session_id: str
    workflow_id: str
    retry_attempt: int
    max_retries: int  # optional
    next_execution_time: str
    delay_ms: int


class EndRunError(TypedDict, total=False):
    message: str
    error_id: str
    full_url: str  # optional
    created_at: str
    error_code: str  # optional
    action_type: str  # optional
    action_display_name: str  # optional
    llm_error_category: str  # optional


class EndRunPayload(TypedDict, total=False):
    session_id: str
    workflow_id: str
    data: Any
    input_variables: Dict[str, Any]
    errors: List[EndRunError]
    status: Literal["execution.success", "execution.failed", "execution.stopped"]
    encrypted_variables: Union[List[str], None]
    file_urls: Union[List[Any], None]


class ExecutionStoppedEarlyPayload(TypedDict):
    message: str
    error_code: str
    session_id: str


class FileUploadedPayload(TypedDict):
    signed_file_url: str
    file_name: str
    timestamp: str
    signed_file_url_expires: str
    metadata: Dict[str, Any]
    session_id: str


class ScreenshotUploadedPayload(TypedDict):
    screenshot_id: str
    signed_screenshot_url: str
    node_display_name: str
    node_id: str
    timestamp: str
    signed_screenshot_url_expires: str
    error_screenshot: bool
    retry_index: int
    full_length_screenshot: bool
    session_id: str


# Type variable for generic webhook messages
E = TypeVar('E', bound=str)


# Generic Webhook Message type
class WebhookMessage(TypedDict, Generic[E], total=False):
    event: E
    timestamp: int
    expires_at: int
    payload: Any  # Will be typed more specifically with EventPayloadMap
    metadata: Dict[str, Any]  # optional


# Generic SSE Run Event Message type
class RunEventMessageData(TypedDict, Generic[E]):
    event: E
    payload: Any
    timestamp: int
    expires_at: int


class RunEventMessage(TypedDict, Generic[E]):
    event: Literal["run.event"]
    data: RunEventMessageData[E]
    timestamp: str
    expires_at: str
