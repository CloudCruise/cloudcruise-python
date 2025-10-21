from __future__ import annotations

import hmac
import hashlib
import json

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
    raw_body: bytes,
    received_signature: str,
    secret_key: str,
    options: WebhookVerificationOptions | None = None,
) -> WebhookPayload:
    if not raw_body:
        raise VerificationError("Received request without body", 400)
    if not received_signature:
        raise VerificationError("Missing HMAC signature", 400)
    if not secret_key:
        raise VerificationError("Missing secret key", 400)

    try:
        data_string = raw_body.decode("utf-8")
    except UnicodeDecodeError as e:
        raise VerificationError(f"Failed to decode body as UTF-8: {str(e)}", 400)

    try:
        data_json = json.loads(data_string)
    except Exception as e:
        raise VerificationError(f"Failed to decode JSON: {str(e)}", 400)

    expires_at = data_json.get("expires_at")
    if not expires_at:
        raise VerificationError("No expiration date sent", 400)

    if not _verify_hmac(data_string, received_signature, secret_key):
        raise VerificationError("Invalid HMAC signature", 401)

    if not (options and options.allowExpired) and (int(__import__('time').time()) > int(expires_at)):
        raise VerificationError("Webhook message expired", 400)

    return data_json  # type: ignore

