from __future__ import annotations

from typing import Optional

from .utils import verify_message
from .types import WebhookPayload, WebhookVerificationOptions


class WebhookClient:
    def __init__(self) -> None:
        pass

    def verify_signature(
        self,
        raw_body: bytes,
        received_signature: str,
        secret_key: str,
        options: Optional[WebhookVerificationOptions] = None,
    ) -> WebhookPayload:
        return verify_message(raw_body, received_signature, secret_key, options)

