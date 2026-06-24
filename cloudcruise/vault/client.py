from __future__ import annotations

from dataclasses import asdict, fields as _dc_fields
from typing import Any, Dict, List, Optional
from .types import (
    GetVaultEntriesFilters,
    ProxyConfig,
    VaultEntry,
    VaultEntryInput,
    VaultTfaCode,
)
from .utils import decrypt_sensitive_fields, encrypt_sensitive_fields


_VAULT_ENTRY_FIELDS = {f.name for f in _dc_fields(VaultEntry)}
_PROXY_FIELDS = {f.name for f in _dc_fields(ProxyConfig)}
_TFA_CODE_FIELDS = {f.name for f in _dc_fields(VaultTfaCode)}


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
        if conflicts:
            raise ValueError(
                "provider-backed vault entries cannot include "
                + ", ".join(conflicts)
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
    return VaultEntry(**known)


class VaultClient:
    def __init__(self, make_request, encryption_key: str) -> None:
        self._make_request = make_request
        self._encryption_key = encryption_key

    def create(self, entry: VaultEntryInput) -> VaultEntry:
        """Create a vault entry.

        Sensitive fields (``user_name``, ``password``, ``tfa_secret``) are
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
            from urllib.parse import urlencode

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

    def get_tfa_code(self, permissioned_user_id: str, domain: str) -> VaultTfaCode:
        """Get the current 2FA code for a single vault entry.

        The code is auto-detected by the credential's 2FA method:
        - authenticator: a freshly generated TOTP, with ``expires_in_seconds``.
        - email: the most recently received code (within the freshness window),
          with ``received_at``.

        SMS and magic-link credentials are not supported (the endpoint returns
        409). The code is returned with ``Cache-Control: no-store`` and should
        not be logged or cached.
        """
        if not permissioned_user_id:
            raise ValueError("permissioned_user_id is required to get a TFA code")
        if not domain:
            raise ValueError("domain is required to get a TFA code")
        from urllib.parse import urlencode

        qs = urlencode(
            {"permissioned_user_id": permissioned_user_id, "domain": domain}
        )
        response = self._make_request("GET", f"/vault/tfa-code?{qs}")
        known = {k: v for k, v in response.items() if k in _TFA_CODE_FIELDS}
        return VaultTfaCode(**known)
