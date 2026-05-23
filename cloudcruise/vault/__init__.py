from __future__ import annotations

from typing import Dict, List, Optional

from .types import VaultEntry, VaultEntryInput, GetVaultEntriesFilters, ProxyConfig, TfaMethod

def _client():
    # Lazy import to avoid circular imports during package initialization
    from .._default import get_client as _get_client
    return _get_client()

__all__ = [
    "VaultEntry",
    "VaultEntryInput",
    "GetVaultEntriesFilters",
    "ProxyConfig",
    "TfaMethod",
    # Convenience APIs
    "create",
    "get",
    "update",
    "delete",
]


def create(entry: VaultEntryInput) -> VaultEntry:
    return _client().vault.create(entry)


def get(filters: Optional[GetVaultEntriesFilters] = None) -> List[VaultEntry]:
    return _client().vault.get(filters)


def update(entry: VaultEntryInput) -> VaultEntry:
    return _client().vault.update(entry)


def delete(params: Dict[str, str]) -> None:
    return _client().vault.delete(params)
