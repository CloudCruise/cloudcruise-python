from __future__ import annotations

import hmac
import hashlib
import json
from typing import Any

from .types import VerificationError, WebhookPayload, WebhookVerificationOptions


def _verify_hmac(received_data: str, received_signature: str, secret_key: str) -> bool:
    mac = hmac.new(secret_key.encode("utf-8"), received_data.encode("utf-8"), hashlib.sha256)
    calculated = mac.hexdigest()
    # received header like: "sha256=<hex>"; split and take hex part if formatted that way
    formatted = received_signature.split("=")[-1]
    if len(formatted) != len(calculated):
        return False
    try:
        return hmac.compare_digest(bytes.fromhex(calculated), bytes.fromhex(formatted))
    except Exception:
        # If not hex-encoded, fallback to string compare_digest
        return hmac.compare_digest(calculated, formatted)


def verify_message(
    received_data: Any,
    received_signature: str,
    secret_key: str,
    options: WebhookVerificationOptions | None = None,
) -> WebhookPayload:
    if not received_data:
        raise VerificationError("Received request without body", 400)
    if not received_signature:
        raise VerificationError("Missing HMAC signature", 400)
    if not secret_key:
        raise VerificationError("Missing secret key", 400)

    if isinstance(received_data, str):
        data_string = received_data
        try:
            data_json = json.loads(received_data)
        except Exception as e:
            raise VerificationError(f"Failed to decode JSON: {str(e)}", 400)
    else:
        data_json = received_data
        data_string = json.dumps(received_data)

    expires_at = data_json.get("expires_at")
    if not expires_at:
        raise VerificationError("No expiration date sent", 400)

    if not _verify_hmac(data_string, received_signature, secret_key):
        raise VerificationError("Invalid HMAC signature", 401)

    if not (options and options.allowExpired) and (int(__import__('time').time()) > int(expires_at)):
        raise VerificationError("Webhook message expired", 400)

    return data_json  # type: ignore

