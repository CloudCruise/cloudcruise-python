from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..runs.types import EventType


class VerificationError(Exception):
    def __init__(self, message: str = "Verification failed", status_code: int = 400) -> None:
        super().__init__(message)
        self.statusCode = status_code


@dataclass
class WebhookPayload:
    event: EventType | str
    expires_at: int
    # Allow arbitrary extra fields
    # mypy: ignore dynamic attributes


@dataclass
class WebhookVerificationOptions:
    allowExpired: Optional[bool] = None

