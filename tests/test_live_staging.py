import json
import os
import time
import unittest
import random
import string

from cloudcruise import CloudCruise, CloudCruiseParams
from cloudcruise.runs.types import StartRunRequest


# Toggle individual tests on/off here
SKIP_WORKFLOWS = True
SKIP_VAULT = True
SKIP_RUNS = True


# Optional inline config (fallbacks to env if unset)
API_KEY = os.environ.get("CLOUDCRUISE_API_KEY") or None
ENCRYPTION_KEY = os.environ.get("CLOUDCRUISE_ENCRYPTION_KEY") or None
BASE_URL = os.environ.get("CLOUDCRUISE_BASE_URL") or "https://api.cloudcruise.com"

# Vault test parameters
VAULT_DOMAIN = None  # e.g., "https://example.com"
VAULT_USER_ID = None  # e.g., "user123"

# Runs test parameters
RUN_WORKFLOW_ID = None  # e.g., "workflow-123"
RUN_INPUT_JSON = None  # e.g., '{"url": "https://example.com"}'


class TestLiveStaging(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not API_KEY or not ENCRYPTION_KEY:
            raise unittest.SkipTest("Provide CLOUDCRUISE_API_KEY and CLOUDCRUISE_ENCRYPTION_KEY or set in file")

        cls.client = CloudCruise(CloudCruiseParams(api_key=API_KEY, base_url=BASE_URL, encryption_key=ENCRYPTION_KEY))

    @unittest.skipIf(SKIP_WORKFLOWS, "workflows test skipped")
    def test_workflows_list(self):
        workflows = self.client.workflows.get_all_workflows()
        self.assertIsInstance(workflows, list)

    @unittest.skipIf(SKIP_VAULT, "vault test skipped")
    def test_vault_crud(self):
        if not VAULT_DOMAIN or not VAULT_USER_ID:
            self.skipTest("Set VAULT_DOMAIN and VAULT_USER_ID in this file to run")

        alias = "sdk-live-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        entry = self.client.vault.create(VAULT_DOMAIN, VAULT_USER_ID, {
            "user_name": "test_user",
            "password": "test_password",
            "tfa_secret": "JBSWY3DPEHPK3PXP",
            "user_alias": alias,
        })
        self.assertTrue(entry.get("id"))

        # Get (filtered, decrypted)
        entries = self.client.vault.get()
        self.assertIsInstance(entries, list)

        from cloudcruise.vault.types import GetVaultEntriesFilters
        filt = self.client.vault.get(GetVaultEntriesFilters(
            permissioned_user_id=VAULT_USER_ID, domain=VAULT_DOMAIN
        ))
        self.assertIsInstance(filt, list)

        # Update
        updated = self.client.vault.update(entry["id"], {"user_alias": alias + "-u"})
        self.assertEqual(updated.get("user_alias"), alias + "-u")

        # Delete
        self.client.vault.delete(VAULT_DOMAIN, VAULT_USER_ID)

    @unittest.skipIf(SKIP_RUNS, "runs test skipped")
    def test_runs_start(self):
        if not RUN_WORKFLOW_ID or not RUN_INPUT_JSON:
            self.skipTest("Set RUN_WORKFLOW_ID and RUN_INPUT_JSON in this file to run")

        try:
            inputs = json.loads(RUN_INPUT_JSON)
        except Exception as e:
            self.skipTest(f"Invalid RUN_INPUT_JSON: {e}")

        req = StartRunRequest(workflow_id=RUN_WORKFLOW_ID, run_input_variables=inputs)
        handle = self.client.runs.start(req)
        self.assertTrue(getattr(handle, "sessionId", None))

        # Let SSE open briefly, then close to avoid long test times
        time.sleep(5)
        handle.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
