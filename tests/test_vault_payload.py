import unittest

from cloudcruise import ProxyConfig, VaultEntry, VaultEntryInput
from cloudcruise.vault.client import _input_to_payload, _to_vault_entry


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


class TestToVaultEntry(unittest.TestCase):
    def test_builds_vault_entry_with_attribute_access(self):
        """The response path must produce a real VaultEntry so callers can do
        ``entry.domain`` as the README documents, not ``entry["domain"]``."""
        response = {
            "id": "vault-1",
            "domain": "https://example.com",
            "permissioned_user_id": "u1",
            "user_name": "alice",
            "tfa_method": "AUTHENTICATOR",
            "created_at": "2026-04-30T00:00:00Z",
        }
        entry = _to_vault_entry(response)
        self.assertIsInstance(entry, VaultEntry)
        self.assertEqual(entry.id, "vault-1")
        self.assertEqual(entry.domain, "https://example.com")
        self.assertEqual(entry.user_name, "alice")
        self.assertEqual(entry.tfa_method, "AUTHENTICATOR")

    def test_drops_unknown_fields(self):
        """Forward-compat: if the backend adds new columns, we don't blow up."""
        response = {
            "domain": "https://example.com",
            "permissioned_user_id": "u1",
            "some_future_field": "hello",
            "another_one": 42,
        }
        entry = _to_vault_entry(response)
        self.assertIsInstance(entry, VaultEntry)
        self.assertFalse(hasattr(entry, "some_future_field"))

    def test_reconstructs_nested_proxy_config(self):
        response = {
            "domain": "https://example.com",
            "permissioned_user_id": "u1",
            "proxy": {"enable": True, "target_ip": "1.2.3.4"},
        }
        entry = _to_vault_entry(response)
        self.assertIsInstance(entry.proxy, ProxyConfig)
        self.assertTrue(entry.proxy.enable)
        self.assertEqual(entry.proxy.target_ip, "1.2.3.4")

    def test_proxy_without_enable_is_left_as_dict(self):
        """Defensive: ProxyConfig requires ``enable``. If the server sends an
        incomplete proxy object, leave it as a dict rather than crashing."""
        response = {
            "domain": "https://example.com",
            "permissioned_user_id": "u1",
            "proxy": {"target_ip": "1.2.3.4"},
        }
        entry = _to_vault_entry(response)
        self.assertIsInstance(entry.proxy, dict)


if __name__ == "__main__":
    unittest.main()
