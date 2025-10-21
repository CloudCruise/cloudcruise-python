from __future__ import annotations

from typing import Optional

from .types import *  # re-export types for convenience

def _client():
    # Lazy import to avoid circular imports during package initialization
    from .._default import get_client as _get_client
    return _get_client()

__all__ = [
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
    "RunHandle",
    "RunStreamOptions",
    "SseEventName",
    "SseMessage",
    "RunEventEnvelope",
    # Convenience APIs
    "start",
    "subscribe_to_session",
    "submit_user_interaction",
    "get_results",
    "interrupt",
    "replay_webhooks",
]


def start(request: StartRunRequest, options: Optional[RunStreamOptions] = None) -> RunHandle:
    return _client().runs.start(request, options)


def subscribe_to_session(session_id: str, options: Optional[RunStreamOptions] = None) -> RunHandle:
    return _client().runs.subscribe_to_session(session_id, options)


def submit_user_interaction(session_id: str, data: UserInteractionData) -> None:
    return _client().runs.submit_user_interaction(session_id, data)


def get_results(session_id: str) -> RunResult:
    return _client().runs.get_results(session_id)


def interrupt(session_id: str) -> None:
    return _client().runs.interrupt(session_id)


def replay_webhooks(session_id: str) -> WebhookReplayResponse:
    return _client().runs.replay_webhooks(session_id)
