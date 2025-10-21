from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import json
import requests

from .utils.env import get_env
from .vault.client import VaultClient
from .workflows.client import WorkflowsClient
from .runs.client import RunsClient
from .webhook.client import WebhookClient
from .utils.connection_manager import ConnectionManager

@dataclass
class CloudCruiseParams:
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    encryption_key: Optional[str] = None


class CloudCruise:
    """
    CloudCruise Python SDK
    Official client library for the CloudCruise Platform
    """

    # Expose typed attributes for IDE autocomplete
    vault: VaultClient
    workflows: WorkflowsClient
    runs: RunsClient
    webhook: WebhookClient

    def __init__(self, params: Optional[CloudCruiseParams] = None) -> None:
        params = params or CloudCruiseParams()
        api_key = params.api_key or get_env("CLOUDCRUISE_API_KEY")
        base_url = params.base_url or get_env("CLOUDCRUISE_BASE_URL") or "https://api.cloudcruise.com"
        encryption_key = params.encryption_key or get_env("CLOUDCRUISE_ENCRYPTION_KEY")

        if not api_key:
            raise ValueError("Missing apiKey. Provide via params.api_key or CLOUDCRUISE_API_KEY env var.")
        if not encryption_key:
            raise ValueError(
                "Missing encryptionKey. Provide via params.encryption_key or CLOUDCRUISE_ENCRYPTION_KEY env var."
            )

        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._encryption_key = encryption_key

        # Initialize namespace clients
        self._connection_manager = ConnectionManager(self._base_url, self._api_key)
        self.vault = VaultClient(self._make_request, self._encryption_key)
        self.workflows = WorkflowsClient(self._make_request)
        self.runs = RunsClient(self._connection_manager, self._make_request, self.workflows)
        self.webhook = WebhookClient()

    def _make_request(self, method: str, path: str, body: Optional[Any] = None) -> Any:
        """
        Makes an HTTP request to the CloudCruise API
        Automatically adds the cc-key header for authentication
        """
        url = f"{self._base_url}{path}"
        headers = {
            "cc-key": self._api_key,
        }
        try:
            # Only send Content-Type when we have a JSON body
            if body is not None:
                headers["Content-Type"] = "application/json"

            resp = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=(json.dumps(body) if body is not None else None),
                timeout=60,
            )
            if not resp.ok:
                error_text = resp.text
                error_message = f"HTTP {resp.status_code}: {resp.reason}"
                try:
                    error_json = resp.json()
                    error_message = error_json.get("message") or error_json.get("error") or error_message
                except Exception:
                    pass
                raise RuntimeError(error_message)

            ctype = resp.headers.get("content-type", "")
            if "application/json" in ctype:
                return resp.json()

            else:
                return resp.text
        except Exception as e:
            raise e
