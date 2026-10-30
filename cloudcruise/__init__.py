from .cloudcruise import CloudCruise, CloudCruiseParams

from .vault.types import (
    VaultEntry,
    VaultEntryInput,
    GetVaultEntriesFilters,
    ProxyConfig,
    TfaMethod,
    VaultTfaCode,
)

from .secret_providers.types import (
    SecretProvider,
    SecretProviderItem,
    SecretProviderType,
)

from .workflows.types import (
    Workflow,
    WorkflowInputSchema,
    WorkflowMetadata,
    WorkflowVaultSchemaEntry,
    InputValidationError,
    SchemaErrorDetail,
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
    LiveViewConnection,
    VideoUrl,
    FileUrl,
    ScreenshotUrl,
    RunError,
    RunResult,
    WebhookEvent,
    WebhookReplayResponse,
    FlattenedRunEvent,
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

# Modal recovery types (execution.input_required + non_dismissible_popup)
from .events.types import (
    AvailableAction,
    PopupRetry,
    PopupContext,
    ExecutionInputRequiredPayload,
)

from .events.types import (
    ExecutionPasswordRecoveryPayload,
    ExecutionPasswordUpdatedPayload,
    RecoveryErrorCategory,
    RecoveryWebhookEventPayload,
    AgentRecoveryPayload,
    AgentDecisionRequestedPayload,
    AgentDecisionAnsweredPayload,
)

from .webhook.types import WebhookPayload, WebhookVerificationOptions, VerificationError, WebhookMessage
from ._default import get_client as client

__all__ = [
    "CloudCruise",
    "CloudCruiseParams",
    # Default client helper
    "client",
    # Vault Types
    "VaultEntry",
    "VaultEntryInput",
    "GetVaultEntriesFilters",
    "ProxyConfig",
    "TfaMethod",
    "VaultTfaCode",
    # Secret Provider Types
    "SecretProvider",
    "SecretProviderItem",
    "SecretProviderType",
    # Workflow Types
    "Workflow",
    "WorkflowInputSchema",
    "WorkflowMetadata",
    "WorkflowVaultSchemaEntry",
    "InputValidationError",
    "SchemaErrorDetail",
    # Run Types
    "EventType",
    "DryRun",
    "Metadata",
    "RunSpecificWebhook",
    "PayloadWebhook",
    "StartRunRequest",
    "StartRunResponse",
    "UserInteractionData",
    "LiveViewConnection",
    "VideoUrl",
    "FileUrl",
    "ScreenshotUrl",
    "RunError",
    "RunResult",
    "WebhookEvent",
    "WebhookReplayResponse",
    "FlattenedRunEvent",
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
    # Modal Recovery Types
    "AvailableAction",
    "PopupRetry",
    "PopupContext",
    "ExecutionInputRequiredPayload",
    # Recovery and Decision Required Types
    "ExecutionPasswordRecoveryPayload",
    "ExecutionPasswordUpdatedPayload",
    "RecoveryErrorCategory",
    "RecoveryWebhookEventPayload",
    "AgentRecoveryPayload",
    "AgentDecisionRequestedPayload",
    "AgentDecisionAnsweredPayload",
    # Webhook Types
    "WebhookPayload",
    "WebhookVerificationOptions",
    "VerificationError",
    "WebhookMessage",
]
