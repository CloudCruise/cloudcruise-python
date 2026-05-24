from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional


TfaMethod = Literal["AUTHENTICATOR", "EMAIL", "SMS", "MAGIC_LINK"]


@dataclass
class ProxyConfig:
    enable: bool
    target_ip: Optional[str] = None


@dataclass
class VaultEntryInput:
    """Fields a client can set when creating or updating a vault entry.

    Omits server-managed fields (``id``, ``created_at``, ``workspace_id``,
    ``organization_id``, ``site_identifier``, ``session_data_set_at``,
    ``effective_expires_at``) and server-computed reflections
    (``tfa_email``, ``tfa_phone_number``). Those only appear on
    :class:`VaultEntry` responses.
    """

    domain: str
    permissioned_user_id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    password: Optional[str] = None
    tfa_secret: Optional[str] = None
    tfa_method: Optional[TfaMethod] = None
    user_agent: Optional[str] = None
    user_alias: Optional[str] = None
    location: Optional[str] = None
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    allow_multiple_sessions: Optional[bool] = None
    max_concurrency: Optional[int] = None
    prevent_concurrency_during_login: Optional[bool] = None
    cookies: Optional[Any] = None
    local_storage: Optional[Any] = None
    session_storage: Optional[Any] = None
    persist_cookies: Optional[bool] = None
    persist_local_storage: Optional[bool] = None
    persist_session_storage: Optional[bool] = None
    cookie_domain_to_store: Optional[str] = None
    skip_csrf_cookies: Optional[bool] = None
    proxy: Optional[ProxyConfig | dict[str, Any]] = None
    proxy_string: Optional[str] = None
    expiry_time_from_last_use: Optional[str] = None
    expiry_time_from_session_data_set: Optional[str] = None


@dataclass
class VaultEntry:
    """Full shape of a vault entry as returned by the API.

    Includes all writable fields plus server-managed fields
    (``id``, ``workspace_id``, ``organization_id``, ``site_identifier``,
    ``created_at``) and server-computed reflections
    (``tfa_email``, ``tfa_phone_number``, ``session_data_set_at``,
    ``effective_expires_at``). Setting any of the latter on create/update
    requests has no effect; the server ignores them.
    """

    domain: str
    permissioned_user_id: str
    id: Optional[str] = None
    workspace_id: Optional[str] = None
    organization_id: Optional[str] = None
    site_identifier: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    password: Optional[str] = None
    tfa_secret: Optional[str] = None
    tfa_method: Optional[TfaMethod] = None
    tfa_email: Optional[str] = None
    tfa_phone_number: Optional[str] = None
    user_agent: Optional[str] = None
    user_alias: Optional[str] = None
    location: Optional[str] = None
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    allow_multiple_sessions: Optional[bool] = None
    max_concurrency: Optional[int] = None
    prevent_concurrency_during_login: Optional[bool] = None
    cookies: Optional[Any] = None
    local_storage: Optional[Any] = None
    session_storage: Optional[Any] = None
    persist_cookies: Optional[bool] = None
    persist_local_storage: Optional[bool] = None
    persist_session_storage: Optional[bool] = None
    cookie_domain_to_store: Optional[str] = None
    skip_csrf_cookies: Optional[bool] = None
    proxy: Optional[ProxyConfig] = None
    proxy_string: Optional[str] = None
    expiry_time_from_last_use: Optional[str] = None
    expiry_time_from_session_data_set: Optional[str] = None
    session_data_set_at: Optional[str] = None
    effective_expires_at: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class GetVaultEntriesFilters:
    permissioned_user_id: Optional[str] = None
    domain: Optional[str] = None
    decryptCredentials: Optional[bool] = None
