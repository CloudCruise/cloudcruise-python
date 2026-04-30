import unittest

from cloudcruise import ProxyConfig, VaultEntryInput
from cloudcruise.vault.client import _input_to_payload


class TestVaultInputToPayload(unittest.TestCase):
    def test_strips_top_level_none_values(self):
        entry = VaultEntryInput(
            domain="https://example.com",
            permissioned_user_id="u1",
            user_name="alice",
        )
        payload = _input_to_payload(entry)
        self.assertEqual(
            payload,
            {
                "domain": "https://example.com",
                "permissioned_user_id": "u1",
                "user_name": "alice",
            },
        )

    def test_strips_none_inside_nested_proxy(self):
        entry = VaultEntryInput(
            domain="https://example.com",
            permissioned_user_id="u1",
            proxy=ProxyConfig(enable=True),
        )
        payload = _input_to_payload(entry)
        self.assertEqual(payload.get("proxy"), {"enable": True})

    def test_keeps_target_ip_when_set(self):
        entry = VaultEntryInput(
            domain="https://example.com",
            permissioned_user_id="u1",
            proxy=ProxyConfig(enable=True, target_ip="1.2.3.4"),
        )
        payload = _input_to_payload(entry)
        self.assertEqual(
            payload.get("proxy"),
            {"enable": True, "target_ip": "1.2.3.4"},
        )

    def test_preserves_user_blobs_verbatim(self):
        """cookies / local_storage / session_storage are opaque user data and
        may legitimately contain ``None``; we must not recurse into them."""
        cookies = [{"name": "sid", "value": "abc", "expires": None}]
        entry = VaultEntryInput(
            domain="https://example.com",
            permissioned_user_id="u1",
            cookies=cookies,
        )
        payload = _input_to_payload(entry)
        self.assertEqual(payload["cookies"], cookies)


if __name__ == "__main__":
    unittest.main()
