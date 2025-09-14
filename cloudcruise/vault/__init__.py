from __future__ import annotations

from typing import Any, Dict, Optional

from .types import VaultEntry, GetVaultEntriesFilters, ProxyConfig, VaultPostPutHeadersInBody
from .._default import get_client as _client

__all__ = [
    "VaultEntry",
    "GetVaultEntriesFilters",
    "ProxyConfig",
    "VaultPostPutHeadersInBody",
    # Convenience APIs
    "create",
    "get",
    "update",
    "delete",
]


def create(
    domain: str,
    permissioned_user_id: str,
    options: Optional[Dict[str, Any]] = None,
) -> VaultEntry:
    return _client().vault.create(domain, permissioned_user_id, options)


def get(filters: Optional[GetVaultEntriesFilters] = None):
    return _client().vault.get(filters)


def update(updates: Dict[str, Any]) -> VaultEntry:
    return _client().vault.update(updates)


def delete(params: Dict[str, str]) -> None:
    return _client().vault.delete(params)
