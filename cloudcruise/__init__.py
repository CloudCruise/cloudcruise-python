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
)

from .webhook.types import WebhookPayload, WebhookVerificationOptions, VerificationError

from typing import TYPE_CHECKING, Optional

# Help type checkers and IDEs discover subpackages as attributes of the package
if TYPE_CHECKING:  # pragma: no cover
    from . import workflows as workflows
    from . import vault as vault
    from . import runs as runs
    from . import webhook as webhook

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
    # Types
    "VaultEntry",
    "GetVaultEntriesFilters",
    "ProxyConfig",
    "VaultPostPutHeadersInBody",
    "Workflow",
    "WorkflowInputSchema",
    "WorkflowMetadata",
    "InputValidationError",
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
    "WebhookPayload",
    "WebhookVerificationOptions",
    "VerificationError",
]

# Lazy import subpackages so `cloudcruise.workflows` etc. are available without explicit import
def __getattr__(name: str):  # PEP 562
    if name in {"workflows", "vault", "runs", "webhook"}:
        import importlib
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# Provide a cached default client built from environment variables unless
# explicit parameters are provided. Enables module-level convenience APIs.
_default_client: Optional[CloudCruise] = None

def client(params: Optional[CloudCruiseParams] = None) -> CloudCruise:
    global _default_client
    if params is not None or _default_client is None:
        _default_client = CloudCruise(params)
    return _default_client
