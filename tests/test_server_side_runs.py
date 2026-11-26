import json
import os
import unittest
from unittest.mock import patch

from cloudcruise import CloudCruise, CloudCruiseParams, GetVaultEntriesFilters, StartRunRequest, VaultEntryInput


class _OkResponse:
    ok = True
    status_code = 200
    reason = "OK"
    headers = {"content-type": "application/json"}

    def __init__(self, body):
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


def _client_without_key() -> CloudCruise:
    return CloudCruise(CloudCruiseParams(api_key="test-key"))


@patch.dict(os.environ, {"CLOUDCRUISE_ENCRYPTION_KEY": ""})
class TestServerSideRuns(unittest.TestCase):
    def test_client_without_encryption_key_is_created_because_only_the_vault_encrypts(self):
        _client_without_key()

    def test_vault_writes_and_decrypting_reads_refuse_without_a_key_before_any_request(self):
        client = _client_without_key()
        entry = VaultEntryInput(domain="https://example.com", permissioned_user_id="user-1", user_name="a", password="b")
        with patch("cloudcruise.cloudcruise.requests.request") as request:
            for call in (
                lambda: client.vault.create(entry),
                lambda: client.vault.update(entry),
                lambda: client.vault.get(GetVaultEntriesFilters(domain="https://example.com")),
            ):
                with self.assertRaisesRegex(ValueError, "Missing encryptionKey"):
                    call()
            request.assert_not_called()

    def test_vault_get_without_decryption_works_without_a_key_and_returns_stored_values(self):
        client = _client_without_key()
        stored = [{"domain": "https://example.com", "permissioned_user_id": "user-1", "password": "ciphertext"}]
        with patch("cloudcruise.cloudcruise.requests.request", return_value=_OkResponse(stored)):
            entries = client.vault.get(GetVaultEntriesFilters(decryptCredentials=False))
        self.assertEqual(entries[0].password, "ciphertext")

    def test_runs_create_sends_only_post_run_without_client_id_and_opens_no_stream(self):
        client = _client_without_key()
        with patch("cloudcruise.cloudcruise.requests.request", return_value=_OkResponse({"session_id": "session-1"})) as request, patch.object(
            client.runs._connection_manager, "connect_if_needed"
        ) as connect:
            result = client.runs.create(StartRunRequest(workflow_id="wf-1", run_input_variables={"USER": "user-1"}))
        self.assertEqual(result.session_id, "session-1")
        self.assertEqual(request.call_count, 1)
        sent = request.call_args.kwargs
        self.assertEqual((sent["method"], sent["url"]), ("POST", "https://api.cloudcruise.com/run"))
        self.assertNotIn("client_id", json.loads(sent["data"]))
        connect.assert_not_called()

    def test_runs_create_accepts_a_plain_dict_request(self):
        client = _client_without_key()
        with patch("cloudcruise.cloudcruise.requests.request", return_value=_OkResponse({"session_id": "session-2"})):
            result = client.runs.create({"workflow_id": "wf-1", "run_input_variables": {}, "client_id": "ignored"})
        self.assertEqual(result.session_id, "session-2")


if __name__ == "__main__":
    unittest.main()
