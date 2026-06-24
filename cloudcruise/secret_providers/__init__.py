from __future__ import annotations

from typing import List

from .types import SecretProvider, SecretProviderItem, SecretProviderType


def _client():
    from .._default import get_client as _get_client

    return _get_client()


__all__ = [
    "SecretProvider",
    "SecretProviderItem",
    "SecretProviderType",
    "list",
    "list_items",
]


def list() -> List[SecretProvider]:
    return _client().secret_providers.list()


def list_items(secret_provider_id: str) -> List[SecretProviderItem]:
    return _client().secret_providers.list_items(secret_provider_id)

