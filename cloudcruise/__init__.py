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

# Import submodules explicitly for IDE autocomplete/IntelliSense
# These imports make the submodules discoverable by IDEs
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
