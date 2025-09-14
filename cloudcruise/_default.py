from __future__ import annotations

from typing import Optional

from .cloudcruise import CloudCruise, CloudCruiseParams

_default_client: Optional[CloudCruise] = None


def get_client(params: Optional[CloudCruiseParams] = None) -> CloudCruise:
    global _default_client
    if params is not None or _default_client is None:
        _default_client = CloudCruise(params)
    return _default_client

