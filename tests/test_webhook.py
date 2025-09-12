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
        body = {"event": "execution.success", "expires_at": int(time.time()) + 60, "x": 1}
        body_str = json.dumps(body)
        sig = _sign(body_str, "sekrit")
        verified = client.verify_signature(body_str, sig, "sekrit")
        self.assertEqual(verified["event"], "execution.success")


    def test_verify_signature_expired_rejected(self):
        client = WebhookClient()
        body = {"event": "execution.success", "expires_at": int(time.time()) - 1, "x": 1}
        body_str = json.dumps(body)
        sig = _sign(body_str, "sekrit")
        with self.assertRaises(Exception) as ctx:
            client.verify_signature(body_str, sig, "sekrit")
        self.assertIn("expired", str(ctx.exception).lower())

if __name__ == "__main__":
    unittest.main()
