from __future__ import annotations

from .types import WebhookPayload, WebhookVerificationOptions, VerificationError, WebhookMessage
from .utils import verify_message as verify_signature

__all__ = [
    "WebhookPayload",
    "WebhookVerificationOptions",
    "VerificationError",
    "WebhookMessage",
    # Convenience function (no client needed)
    "verify_signature",
]
