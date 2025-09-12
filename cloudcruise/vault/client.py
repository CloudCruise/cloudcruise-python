from __future__ import annotations

from typing import Any, Dict, List, Optional
from .types import VaultEntry, GetVaultEntriesFilters
from .utils import encrypt_sensitive_fields, decrypt_sensitive_fields


class VaultClient:
    def __init__(self, make_request, encryption_key: str) -> None:
        self._make_request = make_request
        self._encryption_key = encryption_key

    def create(
        self,
        domain: str,
        permissioned_user_id: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> VaultEntry:
        entry: Dict[str, Any] = {
            "domain": domain,
            "permissioned_user_id": permissioned_user_id,
        }
        if options:
            entry.update(options)

        processed = encrypt_sensitive_fields(entry, self._encryption_key)
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

    def update(self, id: str, updates: Dict[str, Any]) -> VaultEntry:
        entry = {"id": id, **updates}
        processed = encrypt_sensitive_fields(entry, self._encryption_key)
        response = self._make_request("PUT", "/vault", processed)
        return decrypt_sensitive_fields(response, self._encryption_key)

    def delete(self, domain: str, permissioned_user_id: str) -> None:
        self._make_request("DELETE", "/vault", {"domain": domain, "permissioned_user_id": permissioned_user_id})
