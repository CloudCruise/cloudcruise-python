"""Optional live-staging smoke tests.

These are skipped by default (disabled ``skipIf`` guards below). Flip a
``skipIf`` to ``False`` and supply credentials via ``tests/.env`` or env vars
to run a specific test.

For a richer end-to-end flow (metadata fetch → vault create → run → cleanup),
see ``scripts/live_e2e.py``.

To run a specific test (after enabling the guard):

    python -m unittest tests.test_live_staging.TestLiveStaging.test_workflows_list -v
"""

import os
import random
import string
import unittest
from pathlib import Path

from dotenv import load_dotenv

from cloudcruise import CloudCruise, CloudCruiseParams, VaultEntryInput
from cloudcruise.vault.types import GetVaultEntriesFilters

load_dotenv(Path(__file__).parent / ".env")

API_KEY = os.environ.get("CLOUDCRUISE_API_KEY") or None
ENCRYPTION_KEY = os.environ.get("CLOUDCRUISE_ENCRYPTION_KEY") or None
BASE_URL = os.environ.get("CLOUDCRUISE_BASE_URL") or "https://api.cloudcruise.com"

VAULT_DOMAIN = "https://example.com"
VAULT_USER_ID = "user123"


class TestLiveStaging(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not API_KEY or not ENCRYPTION_KEY:
            raise unittest.SkipTest(
                "Provide CLOUDCRUISE_API_KEY and CLOUDCRUISE_ENCRYPTION_KEY or set in file"
            )

        cls.client = CloudCruise(
            CloudCruiseParams(
                api_key=API_KEY,
                base_url=BASE_URL,
                encryption_key=ENCRYPTION_KEY,
            )
        )

    @unittest.skipIf(True, "workflows test skipped")
    def test_workflows_list(self):
        workflows = self.client.workflows.get_all_workflows()
        self.assertIsInstance(workflows, list)

    @unittest.skipIf(True, "vault test skipped")
    def test_vault_crud(self):
        if not VAULT_DOMAIN or not VAULT_USER_ID:
            self.skipTest("Set VAULT_DOMAIN and VAULT_USER_ID in this file to run")

        alias = "sdk-live-" + "".join(
            random.choices(string.ascii_lowercase + string.digits, k=8)
        )

        entry = self.client.vault.create(
            VaultEntryInput(
                domain=VAULT_DOMAIN,
                permissioned_user_id=VAULT_USER_ID,
                user_name="test_user",
                password="test_password",
                user_alias=alias,
            )
        )
        self.assertTrue(entry.id)

        self.assertIsInstance(self.client.vault.get(), list)

        filtered = self.client.vault.get(
            GetVaultEntriesFilters(
                permissioned_user_id=VAULT_USER_ID,
                domain=VAULT_DOMAIN,
            )
        )
        self.assertIsInstance(filtered, list)

        updated = self.client.vault.update(
            VaultEntryInput(
                domain=VAULT_DOMAIN,
                permissioned_user_id=VAULT_USER_ID,
                user_name="test_user",
                password="test_password",
                user_alias=alias + "-u",
            )
        )
        self.assertEqual(updated.user_alias, alias + "-u")

        self.client.vault.delete(
            {"domain": VAULT_DOMAIN, "permissioned_user_id": VAULT_USER_ID}
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
