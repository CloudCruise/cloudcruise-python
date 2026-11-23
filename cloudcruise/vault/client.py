from __future__ import annotations

import os
import sys
import warnings
from dataclasses import asdict, fields as _dc_fields
from typing import Any, Dict, List, Optional, Sequence, Union
from urllib.parse import urlencode
from .types import (
    GetVaultEntriesFilters,
    ProxyConfig,
    SiteSettings,
    SiteSettingsEntry,
    SiteSettingsEntryOverrides,
    SiteSettingsKey,
    SiteSettingsValues,
    TfaMethod,
    VaultAdditionalField,
    VaultAdditionalFieldWarning,
    VaultEntry,
    VaultEntryInput,
    VaultSecurityQuestion,
    VaultSecurityQuestionWarning,
    VaultTfaCode,
)
from .utils import decrypt_sensitive_fields, encrypt_sensitive_fields


_PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
_VAULT_ENTRY_FIELDS = {f.name for f in _dc_fields(VaultEntry)}
_PROXY_FIELDS = {f.name for f in _dc_fields(ProxyConfig)}
_TFA_CODE_FIELDS = {f.name for f in _dc_fields(VaultTfaCode)}
_SITE_SETTINGS_VALUE_FIELDS = tuple(f.name for f in _dc_fields(SiteSettingsValues))
_NESTED_LIST_TYPES = {
    key: (cls, tuple(f.name for f in _dc_fields(cls)))
    for key, cls in (
        ("additional_fields", VaultAdditionalField),
        ("additional_field_warnings", VaultAdditionalFieldWarning),
        ("security_questions", VaultSecurityQuestion),
        ("security_question_warnings", VaultSecurityQuestionWarning),
    )
}


def _to_dataclass_list(cls: Any, names: tuple, items: Any) -> Any:
    if not isinstance(items, list):
        return items
    return [
        cls(**{name: item.get(name) for name in names})
        if isinstance(item, dict)
        else item
        for item in items
    ]


def _caller_stacklevel() -> int:
    """Stack level of the first frame outside the cloudcruise package,
    counted from the function that calls this one."""
    level = 1
    frame = sys._getframe(1)
    while frame is not None and frame.f_code.co_filename.startswith(_PACKAGE_DIR):
        frame = frame.f_back
        level += 1
    return level


def _input_to_payload(entry: VaultEntryInput) -> Dict[str, Any]:
    """Convert a :class:`VaultEntryInput` to a request dict, dropping
    ``None`` values so we don't send nulls the backend neither needs nor
    validates cleanly.

    ``asdict`` recurses into nested dataclasses, so we also strip ``None``
    from the ``proxy`` sub-dict. We deliberately do NOT recurse into the
    ``cookies`` / ``local_storage`` / ``session_storage`` blobs: those are
    opaque user-supplied data and their ``None`` values may be meaningful.
    """
    raw = asdict(entry)
    payload: Dict[str, Any] = {k: v for k, v in raw.items() if v is not None}
    proxy = payload.get("proxy")
    if isinstance(proxy, dict):
        payload["proxy"] = {k: v for k, v in proxy.items() if v is not None}
    if not payload.get("pinned_settings"):
        payload.pop("pinned_settings", None)
    if "tfa_method" in payload:
        warnings.warn(
            "tfa_method is deprecated: set tfa_methods. "
            "The API ignores tfa_method when tfa_methods is set.",
            DeprecationWarning,
            stacklevel=_caller_stacklevel(),
        )
    _validate_provider_payload(payload)
    return payload


def _validate_provider_payload(payload: Dict[str, Any]) -> None:
    has_provider_id = "secret_provider_id" in payload
    has_secret_ref = "secret_ref" in payload
    if has_provider_id != has_secret_ref:
        raise ValueError("secret_provider_id and secret_ref must be provided together")

    if "secret_cache_ttl_seconds" in payload:
        ttl = payload["secret_cache_ttl_seconds"]
        if not isinstance(ttl, int) or ttl < 0:
            raise ValueError("secret_cache_ttl_seconds must be a non-negative integer")
        if not has_provider_id:
            raise ValueError(
                "secret_cache_ttl_seconds requires secret_provider_id and secret_ref"
            )

    if has_provider_id:
        direct_secret_fields = ("user_name", "password", "tfa_secret")
        conflicts = [field for field in direct_secret_fields if field in payload]
        conflicts += [
            field
            for field in ("additional_fields", "security_questions")
            if payload.get(field)
        ]
        if conflicts:
            raise ValueError(
                "provider-backed vault entries cannot include "
                + ", ".join(conflicts)
            )


class _Unset:
    """Type of :data:`UNSET`, the "argument not given" marker of
    :meth:`VaultClient.update_site_settings`. ``None`` is a real value there
    (it clears a default), so it cannot also mean "not given"."""

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        return False


UNSET = _Unset()


def _to_site_settings(data: Dict[str, Any]) -> SiteSettings:
    raw_values = data.get("settings")
    values = SiteSettingsValues(
        **{
            name: raw_values.get(name)
            for name in _SITE_SETTINGS_VALUE_FIELDS
            if isinstance(raw_values, dict)
        }
    )
    return SiteSettings(
        id=data["id"],
        domain=data["domain"],
        settings=values,
        entry_count=data.get("entry_count", 0),
        overrides=dict(data.get("overrides") or {}),
    )


def _to_site_settings_entry(data: Dict[str, Any]) -> SiteSettingsEntry:
    return SiteSettingsEntry(
        id=data["id"],
        permissioned_user_id=data["permissioned_user_id"],
        overridden=list(data.get("overridden") or []),
    )


def _to_site_settings_entry_overrides(
    data: Dict[str, Any],
) -> SiteSettingsEntryOverrides:
    return SiteSettingsEntryOverrides(
        id=data["id"],
        domain=data["domain"],
        overridden=list(data.get("overridden") or []),
    )


def _to_vault_entry(data: Dict[str, Any]) -> VaultEntry:
    """Build a :class:`VaultEntry` from a server response dict.

    Drops unknown keys (forward-compat with new backend fields) and
    reconstructs the nested :class:`ProxyConfig` if present. The backend
    normally persists proxy as ``proxy_string``, so a nested proxy object
    on the response is rare but handled defensively.
    """
    known: Dict[str, Any] = {k: v for k, v in data.items() if k in _VAULT_ENTRY_FIELDS}
    proxy = known.get("proxy")
    if isinstance(proxy, dict) and "enable" in proxy:
        known["proxy"] = ProxyConfig(
            **{k: v for k, v in proxy.items() if k in _PROXY_FIELDS}
        )
    for key, (cls, names) in _NESTED_LIST_TYPES.items():
        if key in known:
            known[key] = _to_dataclass_list(cls, names, known[key])
    return VaultEntry(**known)


class VaultClient:
    def __init__(self, make_request, encryption_key: str) -> None:
        self._make_request = make_request
        self._encryption_key = encryption_key

    def create(self, entry: VaultEntryInput) -> VaultEntry:
        """Create a vault entry.

        Sensitive fields (``user_name``, ``password``, ``tfa_secret``, every
        additional field value, every security question and answer) are
        encrypted client-side before transport and decrypted on the response.
        """
        payload = _input_to_payload(entry)
        processed = encrypt_sensitive_fields(payload, self._encryption_key)
        response = self._make_request("POST", "/vault", processed)
        decrypted = decrypt_sensitive_fields(response, self._encryption_key)
        return _to_vault_entry(decrypted)

    def get(self, filters: Optional[GetVaultEntriesFilters] = None) -> List[VaultEntry]:
        path = "/vault"
        if filters and (filters.permissioned_user_id or filters.domain):
            params: Dict[str, Any] = {}
            if filters.permissioned_user_id:
                params["permissioned_user_id"] = filters.permissioned_user_id
            if filters.domain:
                params["domain"] = filters.domain
            qs = urlencode(params)
            path += f"?{qs}"

        response = self._make_request("GET", path)
        raw_entries = response if isinstance(response, list) else [response]

        should_decrypt = not (filters and filters.decryptCredentials is False)
        if should_decrypt:
            raw_entries = [
                decrypt_sensitive_fields(e, self._encryption_key) for e in raw_entries
            ]
        return [_to_vault_entry(e) for e in raw_entries]

    def update(self, entry: VaultEntryInput) -> VaultEntry:
        """Update an existing vault entry.

        ``domain`` and ``permissioned_user_id`` identify the entry and are
        required on :class:`VaultEntryInput`. Sensitive fields are re-encrypted
        automatically.
        """
        payload = _input_to_payload(entry)
        processed = encrypt_sensitive_fields(payload, self._encryption_key)
        response = self._make_request("PUT", "/vault", processed)
        decrypted = decrypt_sensitive_fields(response, self._encryption_key)
        return _to_vault_entry(decrypted)

    def delete(self, params: Dict[str, str]) -> None:
        """
        Deletes a vault entry by domain and permissioned_user_id
        params: { "domain": str, "permissioned_user_id": str }
        """
        if not params.get("domain"):
            raise ValueError("domain is required to delete a vault entry")
        if not params.get("permissioned_user_id"):
            raise ValueError("permissioned_user_id is required to delete a vault entry")
        self._make_request("DELETE", "/vault", params)

    def get_tfa_code(
        self,
        permissioned_user_id: str,
        domain: str,
        method: Optional[TfaMethod] = None,
        field: Optional[str] = None,
    ) -> VaultTfaCode:
        """Get the current 2FA code for a single vault entry.

        ``method`` picks the 2FA method and is required when the entry has
        several ``tfa_methods``. ``field`` names a ``Totp`` additional field
        whose code to return instead of the built-in seed's.

        The code depends on the method:
        - authenticator: a freshly generated TOTP, with ``expires_in_seconds``.
        - email: the most recently received code (within the freshness window),
          with ``received_at``.

        SMS and magic-link codes are not supported (the endpoint returns 409).
        The code is returned with ``Cache-Control: no-store`` and should not be
        logged or cached.
        """
        if not permissioned_user_id:
            raise ValueError("permissioned_user_id is required to get a TFA code")
        if not domain:
            raise ValueError("domain is required to get a TFA code")
        if field is not None and method not in (None, "AUTHENTICATOR"):
            raise ValueError("field requires method AUTHENTICATOR or no method")
        params: Dict[str, str] = {
            "permissioned_user_id": permissioned_user_id,
            "domain": domain,
        }
        if method is not None:
            params["method"] = method
        if field is not None:
            params["field"] = field
        qs = urlencode(params)
        response = self._make_request("GET", f"/vault/tfa-code?{qs}")
        known = {k: v for k, v in response.items() if k in _TFA_CODE_FIELDS}
        return VaultTfaCode(**known)

    def list_site_settings(self) -> List[SiteSettings]:
        """List the workspace's domain settings: the defaults every vault entry
        on a domain inherits unless it sets its own value.

        Each item also carries ``entry_count`` (entries on the domain) and, per
        setting, how many of those entries override it.
        """
        response = self._make_request("GET", "/vault/site-settings")
        return [_to_site_settings(item) for item in response]

    def update_site_settings(
        self,
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
        """Set the defaults of one domain, creating them when the domain has
        none yet.

        ``domain`` is normalised like entry domains (lowercase, no scheme, path
        or www). Only the settings you pass change. Passing ``None`` clears a
        default so the platform default applies; the SDK sends it as an
        explicit ``null``. A setting you do not pass is left out of the request
        and keeps its value. Entries that set their own value keep it.

        ``max_concurrency`` must be at least 1 and ``cookie_domain_to_store``
        at most 128 characters; ``login_workflow_id`` is a workflow UUID.
        """
        if not domain:
            raise ValueError("domain is required to update site settings")
        given: Dict[str, Any] = {
            "max_concurrency": max_concurrency,
            "allow_multiple_sessions": allow_multiple_sessions,
            "prevent_concurrency_during_login": prevent_concurrency_during_login,
            "expiry_time_from_last_use": expiry_time_from_last_use,
            "expiry_time_from_session_data_set": expiry_time_from_session_data_set,
            "persist_cookies": persist_cookies,
            "persist_local_storage": persist_local_storage,
            "persist_session_storage": persist_session_storage,
            "skip_csrf_cookies": skip_csrf_cookies,
            "cookie_domain_to_store": cookie_domain_to_store,
            "login_workflow_id": login_workflow_id,
        }
        body: Dict[str, Any] = {"domain": domain}
        body.update({k: v for k, v in given.items() if not isinstance(v, _Unset)})
        response = self._make_request("PATCH", "/vault/site-settings", body)
        return _to_site_settings(response)

    def list_site_settings_entries(self, domain: str) -> List[SiteSettingsEntry]:
        """List the workspace's vault entries that use the domain's settings,
        each with ``overridden``: the settings it sets itself instead of
        inheriting the domain default."""
        if not domain:
            raise ValueError("domain is required to list the entries of a domain")
        qs = urlencode({"domain": domain})
        response = self._make_request("GET", f"/vault/site-settings/entries?{qs}")
        return [_to_site_settings_entry(item) for item in response]

    def apply_site_settings_defaults(
        self, domain: str, entry_ids: Optional[Sequence[str]] = None
    ) -> SiteSettings:
        """Remove every setting the listed entries set themselves, so they read
        all settings from the domain defaults.

        Without ``entry_ids`` it applies to every entry on the domain. Returns
        the updated domain settings.
        """
        if not domain:
            raise ValueError("domain is required to apply site settings defaults")
        body: Dict[str, Any] = {"domain": domain}
        if entry_ids is not None:
            if len(entry_ids) == 0:
                raise ValueError(
                    "entry_ids must not be empty; omit it to apply to every entry"
                )
            body["entry_ids"] = list(entry_ids)
        response = self._make_request("PATCH", "/vault/site-settings/entries", body)
        return _to_site_settings(response)

    def get_site_settings_overrides(
        self, permissioned_user_id: str, domain: str
    ) -> SiteSettingsEntryOverrides:
        """Get the settings a vault entry stores itself (``overridden``). Every
        other setting is read from the domain settings.

        On an entry, ``max_concurrency=-1`` or a zero interval (``"0 seconds"``) for
        the two expiry settings is an own value that turns the limit off
        although the domain sets one; ``None`` means the entry inherits.
        """
        if not permissioned_user_id:
            raise ValueError("permissioned_user_id is required to get site overrides")
        if not domain:
            raise ValueError("domain is required to get site overrides")
        params: Dict[str, str] = {
            "permissioned_user_id": permissioned_user_id,
            "domain": domain,
        }
        qs = urlencode(params)
        response = self._make_request("GET", f"/vault/site-settings/overrides?{qs}")
        return _to_site_settings_entry_overrides(response)

    def reset_site_settings_overrides(
        self,
        permissioned_user_id: str,
        keys: Sequence[SiteSettingsKey],
        domain: str,
    ) -> SiteSettingsEntryOverrides:
        """Stop a vault entry from overriding the listed settings, so it reads
        them from the domain settings again.

        ``keys`` must name at least one setting. Returns the settings the entry still
        overrides.
        """
        if not permissioned_user_id:
            raise ValueError("permissioned_user_id is required to reset site overrides")
        if not keys:
            raise ValueError("keys must name at least one setting to reset")
        if not domain:
            raise ValueError("domain is required to reset site overrides")
        body: Dict[str, Any] = {
            "permissioned_user_id": permissioned_user_id,
            "keys": list(keys),
            "domain": domain,
        }
        response = self._make_request("PATCH", "/vault/site-settings/overrides", body)
        return _to_site_settings_entry_overrides(response)
