from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Union

from .types import (
    VaultEntry,
    VaultEntryInput,
    GetVaultEntriesFilters,
    ProxyConfig,
    TfaMethod,
    VaultTfaCode,
    VaultFieldType,
    VaultAddress,
    VaultAdditionalField,
    VaultAdditionalFieldWarning,
    VaultSecurityQuestion,
    VaultSecurityQuestionWarning,
    SiteSettings,
    SiteSettingsEntry,
    SiteSettingsEntryOverrides,
    SiteSettingsKey,
    SiteSettingsValues,
)
from .client import UNSET, _Unset

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
    "VaultTfaCode",
    "VaultFieldType",
    "VaultAddress",
    "VaultAdditionalField",
    "VaultAdditionalFieldWarning",
    "VaultSecurityQuestion",
    "VaultSecurityQuestionWarning",
    "SiteSettings",
    "SiteSettingsEntry",
    "SiteSettingsEntryOverrides",
    "SiteSettingsKey",
    "SiteSettingsValues",
    "UNSET",
    # Convenience APIs
    "create",
    "get",
    "update",
    "delete",
    "get_tfa_code",
    "list_site_settings",
    "update_site_settings",
    "list_site_settings_entries",
    "apply_site_settings_defaults",
    "get_site_settings_overrides",
    "reset_site_settings_overrides",
]


def create(entry: VaultEntryInput) -> VaultEntry:
    return _client().vault.create(entry)


def get(filters: Optional[GetVaultEntriesFilters] = None) -> List[VaultEntry]:
    return _client().vault.get(filters)


def update(entry: VaultEntryInput) -> VaultEntry:
    return _client().vault.update(entry)


def delete(params: Dict[str, str]) -> None:
    return _client().vault.delete(params)


def get_tfa_code(
    permissioned_user_id: str,
    domain: str,
    method: Optional[TfaMethod] = None,
    field: Optional[str] = None,
) -> VaultTfaCode:
    return _client().vault.get_tfa_code(permissioned_user_id, domain, method, field)


def list_site_settings() -> List[SiteSettings]:
    return _client().vault.list_site_settings()


def update_site_settings(
    domain: str,
    *,
    max_concurrency: Union[int, None, _Unset] = UNSET,
    allow_multiple_sessions: Union[bool, None, _Unset] = UNSET,
    prevent_concurrency_during_login: Union[bool, None, _Unset] = UNSET,
    expiry_time_from_last_use: Union[str, None, _Unset] = UNSET,
    expiry_time_from_session_data_set: Union[str, None, _Unset] = UNSET,
    persist_cookies: Union[bool, None, _Unset] = UNSET,
    persist_local_storage: Union[bool, None, _Unset] = UNSET,
    persist_session_storage: Union[bool, None, _Unset] = UNSET,
    skip_csrf_cookies: Union[bool, None, _Unset] = UNSET,
    cookie_domain_to_store: Union[str, None, _Unset] = UNSET,
    login_workflow_id: Union[str, None, _Unset] = UNSET,
) -> SiteSettings:
    return _client().vault.update_site_settings(
        domain,
        max_concurrency=max_concurrency,
        allow_multiple_sessions=allow_multiple_sessions,
        prevent_concurrency_during_login=prevent_concurrency_during_login,
        expiry_time_from_last_use=expiry_time_from_last_use,
        expiry_time_from_session_data_set=expiry_time_from_session_data_set,
        persist_cookies=persist_cookies,
        persist_local_storage=persist_local_storage,
        persist_session_storage=persist_session_storage,
        skip_csrf_cookies=skip_csrf_cookies,
        cookie_domain_to_store=cookie_domain_to_store,
        login_workflow_id=login_workflow_id,
    )


def list_site_settings_entries(domain: str) -> List[SiteSettingsEntry]:
    return _client().vault.list_site_settings_entries(domain)


def apply_site_settings_defaults(
    domain: str, entry_ids: Optional[Sequence[str]] = None
) -> SiteSettings:
    return _client().vault.apply_site_settings_defaults(domain, entry_ids)


def get_site_settings_overrides(
    permissioned_user_id: str, domain: str
) -> SiteSettingsEntryOverrides:
    return _client().vault.get_site_settings_overrides(permissioned_user_id, domain)


def reset_site_settings_overrides(
    permissioned_user_id: str,
    keys: Sequence[SiteSettingsKey],
    domain: str,
) -> SiteSettingsEntryOverrides:
    return _client().vault.reset_site_settings_overrides(
        permissioned_user_id, keys, domain
    )
