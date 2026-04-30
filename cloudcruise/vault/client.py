from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional
from .types import VaultEntry, VaultEntryInput, GetVaultEntriesFilters
from .utils import encrypt_sensitive_fields, decrypt_sensitive_fields


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
    return payload


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
        return decrypt_sensitive_fields(response, self._encryption_key)

    def get(self, filters: Optional[GetVaultEntriesFilters] = None):
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
        entries = response if isinstance(response, list) else [response]

        should_decrypt = True
        if filters and filters.decryptCredentials is False:
            should_decrypt = False
        if should_decrypt:
            entries = [decrypt_sensitive_fields(e, self._encryption_key) for e in entries]
        return entries

    def update(self, entry: VaultEntryInput) -> VaultEntry:
        """Update an existing vault entry.

        ``domain`` and ``permissioned_user_id`` identify the entry and are
        required on :class:`VaultEntryInput`. Sensitive fields are re-encrypted
        automatically.
        """
        payload = _input_to_payload(entry)
        processed = encrypt_sensitive_fields(payload, self._encryption_key)
        response = self._make_request("PUT", "/vault", processed)
        return decrypt_sensitive_fields(response, self._encryption_key)

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
