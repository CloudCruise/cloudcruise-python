# Webhook Verification (Python SDK)

Verify CloudCruise webhook requests using HMAC-SHA256 with a shared secret. The
helper validates the raw body, signature, JSON decoding, and expiration.

---

## Quick Start

```python
from cloudcruise.webhook import verify_signature, VerificationError

WEBHOOK_SECRET = "your-webhook-secret"

# raw_body: the exact bytes received on the request
# signature: the signature string from your webhook header (e.g., "sha256=<hex>")

def verify(raw_body: bytes, signature: str) -> dict:
    try:
        payload = verify_signature(raw_body, signature, WEBHOOK_SECRET)
        # payload is the parsed JSON dict; includes at least {"event", "expires_at", ...}
        return payload
    except VerificationError as e:
        # e.statusCode is an int (e.g., 400 for expired/missing, 401 for invalid HMAC)
        raise
```

Notes
- Pass the exact request body bytes. Do not re-encode or pretty-print before verification.
- The signature format may be `sha256=<hex>` or just `<hex>`; both are accepted.
- Payload must include `expires_at` (epoch seconds). Expired payloads are rejected by default.

---

## Framework Examples

Flask
```python
from flask import Flask, request, jsonify, make_response
from cloudcruise.webhook import verify_signature, VerificationError

app = Flask(__name__)
WEBHOOK_SECRET = "your-webhook-secret"

@app.post("/webhooks/cloudcruise")
def cloudcruise_webhook():
    raw = request.get_data(cache=False)  # bytes
    signature = request.headers.get("X-Signature", "")  # use your configured signature header
    try:
        payload = verify_signature(raw, signature, WEBHOOK_SECRET)
        # handle event
        return jsonify({"ok": True}), 200
    except VerificationError as e:
        return make_response(str(e), e.statusCode)
```

FastAPI
```python
from fastapi import FastAPI, Request, Response
from cloudcruise.webhook import verify_signature, VerificationError

app = FastAPI()
WEBHOOK_SECRET = "your-webhook-secret"

@app.post("/webhooks/cloudcruise")
async def cloudcruise_webhook(request: Request):
    raw = await request.body()
    signature = request.headers.get("X-Signature", "")
    try:
        payload = verify_signature(raw, signature, WEBHOOK_SECRET)
        return {"ok": True}
    except VerificationError as e:
        return Response(content=str(e), status_code=e.statusCode)
```

---

## Options

Allow expired messages (useful for testing):
```python
from cloudcruise.webhook import verify_signature, WebhookVerificationOptions

payload = verify_signature(
    raw_body,
    signature,
    secret_key,
    WebhookVerificationOptions(allowExpired=True),
)
```

Client class (equivalent API):
```python
from cloudcruise.webhook.client import WebhookClient
client = WebhookClient()
payload = client.verify_signature(raw_body, signature, secret_key)
```

---

## Error Handling
- Missing body/signature/secret → 400
- Invalid JSON → 400
- Invalid HMAC → 401
- Message expired → 400

The exception type is `VerificationError(message, statusCode)`.

---

## Event Payload
Minimal shape:
```json
{
  "event": "execution.success",
  "expires_at": 1726350000,
  "...": "additional fields"
}
```

Common event types include: execution.queued, execution.start, execution.step,
interaction.waiting, interaction.finished, interaction.failed, execution.stopped,
execution.failed, execution.success.

---

## Testing: Generating a Signature
```python
import hmac, hashlib, json
body = {"event": "execution.success", "expires_at": 2000000000}
body_str = json.dumps(body)
signature = f"sha256={hmac.new(b"sekrit", body_str.encode(), hashlib.sha256).hexdigest()}"
```

Use `verify_signature(body_str.encode(), signature, "sekrit")` to validate.

