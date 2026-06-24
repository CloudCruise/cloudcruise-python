import unittest

from cloudcruise.secret_providers.client import SecretProvidersClient
from cloudcruise.secret_providers.types import SecretProvider, SecretProviderItem


class TestSecretProvidersClient(unittest.TestCase):
    def test_list_secret_providers(self):
        calls = []

        def make_request(method, path, body=None):
            calls.append((method, path, body))
            return [
                {
                    "id": "provider-1",
                    "provider_type": "1password",
                    "name": "Acme 1Password",
                    "cache_ttl_seconds": 300,
                }
            ]

        client = SecretProvidersClient(make_request)
        providers = client.list()

        self.assertEqual(calls, [("GET", "/secret-providers", None)])
        self.assertIsInstance(providers[0], SecretProvider)
        self.assertEqual(providers[0].id, "provider-1")
        self.assertEqual(providers[0].provider_type, "1password")
        self.assertEqual(providers[0].cache_ttl_seconds, 300)

    def test_list_secret_provider_items(self):
        calls = []

        def make_request(method, path, body=None):
            calls.append((method, path, body))
            return [
                {
                    "id": "item-1",
                    "title": "Acme Prod",
                    "vaultName": "Automation",
                    "ref": "op://vault/item-1",
                }
            ]

        client = SecretProvidersClient(make_request)
        items = client.list_items("provider-1")

        self.assertEqual(
            calls, [("GET", "/secret-providers/provider-1/items", None)]
        )
        self.assertIsInstance(items[0], SecretProviderItem)
        self.assertEqual(items[0].id, "item-1")
        self.assertEqual(items[0].ref, "op://vault/item-1")
        self.assertEqual(items[0].vaultName, "Automation")

    def test_list_items_requires_provider_id(self):
        client = SecretProvidersClient(lambda method, path, body=None: [])

        with self.assertRaisesRegex(ValueError, "secret_provider_id is required"):
            client.list_items("")


if __name__ == "__main__":
    unittest.main()
