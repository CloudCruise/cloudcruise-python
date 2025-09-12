from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class VaultPostPutHeadersInBody:
    header_name: str
    header_value: str


@dataclass
class ProxyConfig:
    enable: Optional[bool] = None
    target_ip: Optional[str] = None


@dataclass
class VaultEntry:
    id: Optional[str]
    domain: str
    permissioned_user_id: str
    workspace_id: Optional[str] = None
    user_id: Optional[str] = None
    password: Optional[str] = None
    user_name: Optional[str] = None
    tfa_secret: Optional[str] = None
    user_agent: Optional[str] = None
    user_alias: Optional[str] = None
    location: Optional[str] = None
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    allow_multiple_sessions: Optional[bool] = None
    cookies: Optional[Any] = None
    local_storage: Optional[Any] = None
    session_storage: Optional[Any] = None
    persist_cookies: Optional[bool] = None
    persist_local_storage: Optional[bool] = None
    persist_session_storage: Optional[bool] = None
    cookie_domain_to_store: Optional[str] = None
    proxy: Optional[ProxyConfig] = None
    proxy_string: Optional[str] = None
    headers: Optional[List[VaultPostPutHeadersInBody]] = None
    created_at: Optional[str] = None


@dataclass
class GetVaultEntriesFilters:
    permissioned_user_id: Optional[str] = None
    domain: Optional[str] = None
    decryptCredentials: Optional[bool] = None

