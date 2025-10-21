from __future__ import annotations

from typing import Optional

from .cloudcruise import CloudCruise, CloudCruiseParams

_default_client: Optional[CloudCruise] = None


def get_client(
    params: Optional[CloudCruiseParams] = None,
    *,
    api_key: Optional[str] = None,
    encryption_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> CloudCruise:
    """Return the shared default CloudCruise client.

    You can configure it by passing a CloudCruiseParams instance or via
    keyword args (api_key, encryption_key, base_url). Passing any params or
    keyword args replaces the cached client.
    """
    global _default_client

    effective_params = params
    if effective_params is None and (api_key is not None or encryption_key is not None or base_url is not None):
        effective_params = CloudCruiseParams(api_key=api_key, encryption_key=encryption_key, base_url=base_url)

    if effective_params is not None or _default_client is None:
        _default_client = CloudCruise(effective_params)
    return _default_client
