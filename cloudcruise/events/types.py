from __future__ import annotations

from typing import Any, Dict, Generic, List, Literal, TypeVar, Union

from typing_extensions import NotRequired, TypedDict

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


class ExecutionPasswordRecoveryPayload(TypedDict, total=False):
    session_id: str
    workflow_id: str
    phase: Literal["started", "analyzing_form", "submitting", "verifying", "resuming", "completed", "failed"]
    message: str
    resume_mode: Literal["login", "original_node"]  # optional


class ExecutionPasswordUpdatedPayload(TypedDict):
    session_id: str
    workflow_id: str


RecoveryErrorCategory = Literal[
    "XPATH_INCORRECT",
    "INCORRECT_INPUTS",
    "UNEXPECTED_UI_STATE",
    "AUTHENTICATION_ERROR",
    "PASSWORD_UPDATE_REQUIRED",
    "PAGE_STILL_LOADING",
    "SERVICE_UNAVAILABLE",
    "NOT_CONFIDENT",
    "INTERNAL_ERROR",
    "IGNORE_ERROR",
]


class RecoveryWebhookEventPayload(TypedDict):
    category: RecoveryErrorCategory
    subType: str | None
    outcome: Literal["resume", "requeue", "fail"]
    resumeNodeTitle: str | None


class AgentRecoveryPayload(RecoveryWebhookEventPayload):
    session_id: str
    workflow_id: str


DecisionWebhookOutcome = Literal["answered", "declined", "expired", "cancelled", "failed"]

DecisionWebhookAnsweredVia = Literal["slack", "web", "api"]

DecisionWebhookDirective = Literal["requeue", "add_error_code", "fail"]

DecisionWebhookFieldValue = str | int | float | bool | list[str]


class DecisionWebhookOption(TypedDict):
    id: str
    label: str
    note: NotRequired[str]


class DecisionWebhookField(TypedDict):
    id: str
    label: str
    type: str
    options: NotRequired[list[DecisionWebhookOption]]
    required: NotRequired[Literal[False]]
    min: NotRequired[float]
    max: NotRequired[float]
    placeholder: NotRequired[str]
    hint: NotRequired[str]


class DecisionRequestedWebhookEventPayload(TypedDict):
    decision_id: str
    question: str
    context: str
    fields: list[DecisionWebhookField]
    free_text: bool
    respond_url: str


class DecisionWebhookAnswer(TypedDict, total=False):
    values: dict[str, DecisionWebhookFieldValue]
    text: str
    directive: DecisionWebhookDirective


class DecisionAnsweredWebhookEventPayload(TypedDict):
    decision_id: str
    outcome: DecisionWebhookOutcome
    answered_via: NotRequired[DecisionWebhookAnsweredVia]
    answered_by: NotRequired[str]
    answer: NotRequired[DecisionWebhookAnswer]


class AgentDecisionRequestedPayload(DecisionRequestedWebhookEventPayload):
    session_id: str
    workflow_id: str


class AgentDecisionAnsweredPayload(DecisionAnsweredWebhookEventPayload):
    session_id: str
    workflow_id: str


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
