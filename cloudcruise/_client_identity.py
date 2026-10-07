from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


def _client_header_value() -> str:
    try:
        return f"sdk-python/{version('cloudcruise')}"
    except PackageNotFoundError:
        return "sdk-python"


CLIENT_IDENTITY_HEADERS = {"X-CloudCruise-Client": _client_header_value()}
