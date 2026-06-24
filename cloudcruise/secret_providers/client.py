from __future__ import annotations

from typing import Any, Dict, List

from .types import SecretProvider, SecretProviderItem


def _to_secret_provider(data: Dict[str, Any]) -> SecretProvider:
    return SecretProvider(
        id=data["id"],
        provider_type=data["provider_type"],
        name=data["name"],
        cache_ttl_seconds=data.get("cache_ttl_seconds"),
    )


def _to_secret_provider_item(data: Dict[str, Any]) -> SecretProviderItem:
    return SecretProviderItem(
        id=data["id"],
        title=data["title"],
        ref=data["ref"],
        vaultName=data.get("vaultName"),
    )


class SecretProvidersClient:
    def __init__(self, make_request) -> None:
        self._make_request = make_request

    def list(self) -> List[SecretProvider]:
        response = self._make_request("GET", "/secret-providers")
        providers = response if isinstance(response, list) else [response]
        return [_to_secret_provider(provider) for provider in providers]

    def list_items(self, secret_provider_id: str) -> List[SecretProviderItem]:
        if not secret_provider_id:
            raise ValueError("secret_provider_id is required")

        response = self._make_request(
            "GET", f"/secret-providers/{secret_provider_id}/items"
        )
        items = response if isinstance(response, list) else [response]
        return [_to_secret_provider_item(item) for item in items]

