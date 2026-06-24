from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


SecretProviderType = Literal["1password"]


@dataclass
class SecretProvider:
    id: str
    provider_type: SecretProviderType
    name: str
    cache_ttl_seconds: Optional[int] = None


@dataclass
class SecretProviderItem:
    id: str
    title: str
    ref: str
    vaultName: Optional[str] = None

