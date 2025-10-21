from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Literal, Optional, Protocol, TypedDict, Union

# Import event payload types for re-export
from ..events.types import (
    ExecutionQueuedPayload,
    ExecutionStartPayload,
    ExecutionStepPayload,
    InteractionWaitingPayload,
    InteractionFinishedPayload,
    AgentErrorAnalysisPayload,
    ExecutionRequeuedPayload,
    EndRunPayload,
    EndRunError,
    ExecutionStoppedEarlyPayload,
    FileUploadedPayload,
    ScreenshotUploadedPayload,
    WebhookMessage as EventWebhookMessage,
    RunEventMessage,
)


EventType = Literal[
    "execution.queued",
    "execution.start",
    "execution.step",
    "execution.pause",
    "execution.stopped",
    "execution.failed",
    "execution.success",
    "execution.requeued",
    "file.uploaded",
    "screenshot.uploaded",
    "video.uploaded",
    "interaction.waiting",
    "interaction.finished",
    "interaction.failed",
    "agent.error_analysis",
]


@dataclass
class DryRun:
    enabled: bool
    add_to_output: Optional[Dict[str, Any]] = None


@dataclass
class Metadata:
    metadata: Dict[str, Any]


@dataclass
class RunSpecificWebhook:
    url: str
    event_types_subscribed: List[EventType]
    secret: str
    validity: int


PayloadWebhook = Union[Metadata, RunSpecificWebhook]


@dataclass
class StartRunRequest:
    workflow_id: str
    run_input_variables: Dict[str, Any]
    dry_run: Optional[DryRun] = None
    webhook: Optional[PayloadWebhook] = None
    additional_context: Optional[Dict[str, Any]] = None
    client_id: Optional[str] = None


@dataclass
class StartRunResponse:
    session_id: str


UserInteractionData = Dict[str, Any]


@dataclass
class VideoUrl:
    timestamp: str
    session_id: str
    signed_screen_recording_url: str
    signed_screen_recording_url_expires: str


@dataclass
class FileUrl:
    signed_file_url: str
    file_name: str
    timestamp: str
    signed_file_url_expires: str
    metadata: Dict[str, Any]


@dataclass
class ScreenshotUrl:
    signed_screenshot_url: str
    node_display_name: str
    timestamp: str
    signed_screenshot_url_expires: str
    error_screenshot: bool


@dataclass
class RunError:
    prompt: Optional[str] = None
    message: Optional[str] = None
    error_id: Optional[str] = None
    full_url: Optional[str] = None
    llm_model: Optional[str] = None
    created_at: Optional[str] = None
    error_code: Optional[str] = None
    action_type: Optional[str] = None
    action_display_name: Optional[str] = None


@dataclass
class RunResult:
    session_id: str
    status: EventType
    input_variables: Dict[str, Any]
    data: Dict[str, Any]
    video_urls: List[VideoUrl]
    file_urls: List[FileUrl]
    screenshot_urls: List[ScreenshotUrl]
    errors: Optional[List[RunError]]


@dataclass
class WebhookEvent:
    success: bool
    response: str
    error: str


@dataclass
class WebhookReplayResponse:
    status: str
    info: str
    nr_success: int
    nr_failed: int
    webhook_events: List[WebhookEvent]


SseEventName = Literal["run.event", "ping"]


class RunEventData(TypedDict, total=False):
    event: Union[EventType, str]
    payload: Dict[str, Any]
    expires_at: int
    timestamp: int


class RunEventEnvelope(TypedDict, total=False):
    event: Literal["run.event"]
    data: RunEventData
    timestamp: str
    expires_at: str


class PingEnvelope(TypedDict, total=False):
    event: Literal["ping"]
    data: Union[Dict[str, Any], Dict[str, int]]


SseMessage = Union[RunEventEnvelope, PingEnvelope]


@dataclass
class RunStreamOptions:
    # In Python, use a threading.Event to signal stop if desired
    # headers and with_credentials are not used directly in SSE manager
    reconnect_enabled: Optional[bool] = None
    reconnect_delays: Optional[List[float]] = None


class RunHandle(Protocol):
    sessionId: str

    def on(self, event: str, handler) -> Any:
        ...

    def wait(self) -> RunResult:
        ...

    def close(self) -> None:
        ...

    def __iter__(self) -> Iterator[SseMessage]:
        ...


# Export all types including event payloads
__all__ = [
    # Core types
    "EventType",
    "DryRun",
    "Metadata",
    "RunSpecificWebhook",
    "PayloadWebhook",
    "StartRunRequest",
    "StartRunResponse",
    "UserInteractionData",
    "VideoUrl",
    "FileUrl",
    "ScreenshotUrl",
    "RunError",
    "RunResult",
    "WebhookEvent",
    "WebhookReplayResponse",
    "SseEventName",
    "RunEventData",
    "RunEventEnvelope",
    "PingEnvelope",
    "SseMessage",
    "RunStreamOptions",
    "RunHandle",
    # Event payload types (re-exported from events.types)
    "ExecutionQueuedPayload",
    "ExecutionStartPayload",
    "ExecutionStepPayload",
    "InteractionWaitingPayload",
    "InteractionFinishedPayload",
    "AgentErrorAnalysisPayload",
    "ExecutionRequeuedPayload",
    "EndRunPayload",
    "EndRunError",
    "ExecutionStoppedEarlyPayload",
    "FileUploadedPayload",
    "ScreenshotUploadedPayload",
    "EventWebhookMessage",
    "RunEventMessage",
]

