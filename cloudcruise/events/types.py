from __future__ import annotations

from typing import Any, Dict, Generic, List, Literal, TypeVar, Union

from typing_extensions import TypedDict

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
    # Modal-recovery phases (set by the non-dismissible popup loop):
    # - "modal_decision_dispatched": SDK customer submitted a modal_action and
    #   the backend dispatched the synthetic click; modal_action and
    #   modal_action_label identify which CTA was picked.
    # - "popup_dismiss_verified": post-cascade verify hook ran; outcome
    #   indicates whether the modal was actually dismissed.
    phase: str  # optional ("modal_decision_dispatched" | "popup_dismiss_verified")
    session_id: str  # optional
    modal_action: str  # optional, present when phase == "modal_decision_dispatched"
    modal_action_label: str  # optional
    response_time_ms: int  # optional
    outcome: str  # optional, present when phase == "popup_dismiss_verified" ("success" | "failure")
    host: str  # optional
    popup_signature: str  # optional


# === Non-dismissible modal recovery types ===
# When a workflow click is blocked by a modal the worker cannot dismiss on its
# own, the backend emits an execution.input_required event with reason set to
# "non_dismissible_popup" and a popup_context block carrying the visible CTA
# buttons (available_actions) plus a per-session retry counter. Customers
# respond by calling client.runs.submit_modal_action(session_id, action_id).
class AvailableAction(TypedDict):
    id: str
    label: str


class PopupRetry(TypedDict):
    attempt: int
    max_attempts: int


class PopupContext(TypedDict, total=False):
    error_description: str
    error_sub_type: str  # optional ("NON_DISMISSIBLE")
    full_url: str  # optional
    available_actions: List["AvailableAction"]
    retry: "PopupRetry"


class ExecutionInputRequiredPayload(TypedDict, total=False):
    session_id: str
    input_variables: Dict[str, Any]
    screenshot_url: str  # optional
    # Discriminator for which recovery path is requesting input:
    # - "input_required": missing or invalid workflow variable
    # - "incorrect_form_input": form rejected the typed value
    # - "multiple_matching_results": extractor needs disambiguation
    # - "non_dismissible_popup": modal CTA needs to be picked (popup_context set)
    reason: str  # optional
    popup_context: "PopupContext"  # optional, present iff reason == "non_dismissible_popup"


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
    vault_entries: Union[Dict[str, Any], None]


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
