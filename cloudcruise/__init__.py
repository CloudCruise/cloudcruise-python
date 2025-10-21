from .cloudcruise import CloudCruise, CloudCruiseParams

from .vault.types import (
    VaultEntry,
    GetVaultEntriesFilters,
    ProxyConfig,
    VaultPostPutHeadersInBody,
)

from .workflows.types import (
    Workflow,
    WorkflowInputSchema,
    WorkflowMetadata,
    InputValidationError,
)

from .runs.types import (
    EventType,
    DryRun,
    Metadata,
    RunSpecificWebhook,
    PayloadWebhook,
    StartRunRequest,
    StartRunResponse,
    UserInteractionData,
    VideoUrl,
    FileUrl,
    ScreenshotUrl,
    RunError,
    RunResult,
    WebhookEvent,
    WebhookReplayResponse,
    RunHandle,
    RunStreamOptions,
    SseEventName,
    SseMessage,
    RunEventEnvelope,
    # Event payload types
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
    EventWebhookMessage,
    RunEventMessage,
)

from .webhook.types import WebhookPayload, WebhookVerificationOptions, VerificationError, WebhookMessage
from ._default import get_client as client

from typing import TYPE_CHECKING, Optional

# Help type checkers and IDEs discover subpackages as attributes of the package
if TYPE_CHECKING:  # pragma: no cover
    from . import workflows as workflows
    from . import vault as vault
    from . import runs as runs
    from . import webhook as webhook
    from . import events as events

__all__ = [
    "CloudCruise",
    "CloudCruiseParams",
    # Default client helper
    "client",
    # Subpackages (for discoverability)
    "workflows",
    "vault",
    "runs",
    "webhook",
    "events",
    # Vault Types
    "VaultEntry",
    "GetVaultEntriesFilters",
    "ProxyConfig",
    "VaultPostPutHeadersInBody",
    # Workflow Types
    "Workflow",
    "WorkflowInputSchema",
    "WorkflowMetadata",
    "InputValidationError",
    # Run Types
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
    # Event Payload Types
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
    # Webhook Types
    "WebhookPayload",
    "WebhookVerificationOptions",
    "VerificationError",
    "WebhookMessage",
]

# Lazy import subpackages so `cloudcruise.workflows` etc. are available without explicit import
def __getattr__(name: str):  # PEP 562
    if name in {"workflows", "vault", "runs", "webhook", "events"}:
        import importlib
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
