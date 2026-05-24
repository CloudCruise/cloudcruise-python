import json
import time
import hmac
import hashlib
import unittest

from cloudcruise.webhook.client import WebhookClient

def _sign(body: str, secret: str) -> str:
    mac = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"sha256={mac}"

class TestWebhook(unittest.TestCase):
    def test_verify_signature_ok(self):
        client = WebhookClient()
        body = {
            "event": "execution.success",
            "expires_at": int(time.time()) + 60,
            "timestamp": int(time.time()),
            "payload": {"ok": True},
            "metadata": {"source": "test"},
            "x": 1,
        }
        body_str = json.dumps(body)
        body_bytes = body_str.encode("utf-8")
        sig = _sign(body_str, "sekrit")
        verified = client.verify_signature(body_bytes, sig, "sekrit")
        self.assertEqual(verified.event, "execution.success")
        self.assertEqual(verified.payload, {"ok": True})
        self.assertEqual(verified.metadata, {"source": "test"})
        self.assertEqual(verified.data["x"], 1)

    def test_verify_signature_expired_rejected(self):
        client = WebhookClient()
        body = {
            "event": "execution.success",
            "expires_at": int(time.time()) - 1,
            "timestamp": int(time.time()),
            "payload": {},
        }
        body_str = json.dumps(body)
        body_bytes = body_str.encode("utf-8")
        sig = _sign(body_str, "sekrit")
        with self.assertRaises(Exception) as ctx:
            client.verify_signature(body_bytes, sig, "sekrit")
        self.assertIn("expired", str(ctx.exception).lower())

    def test_verify_signature_requires_backend_message_shape(self):
        client = WebhookClient()
        body = {
            "event": "execution.success",
            "expires_at": int(time.time()) + 60,
            "timestamp": int(time.time()),
        }
        body_str = json.dumps(body)
        body_bytes = body_str.encode("utf-8")
        sig = _sign(body_str, "sekrit")
        with self.assertRaises(Exception) as ctx:
            client.verify_signature(body_bytes, sig, "sekrit")
        self.assertIn("payload", str(ctx.exception).lower())

    def test_verify_signature_rejects_non_object_payload(self):
        client = WebhookClient()
        body = {
            "event": "execution.success",
            "expires_at": int(time.time()) + 60,
            "timestamp": int(time.time()),
            "payload": ["not", "an", "object"],
        }
        body_str = json.dumps(body)
        body_bytes = body_str.encode("utf-8")
        sig = _sign(body_str, "sekrit")
        with self.assertRaises(Exception) as ctx:
            client.verify_signature(body_bytes, sig, "sekrit")
        self.assertIn("payload must be an object", str(ctx.exception).lower())

if __name__ == "__main__":
    unittest.main()
