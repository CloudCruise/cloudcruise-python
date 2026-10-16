import unittest

from cloudcruise.runs.client import RunsClient
from cloudcruise.runs.types import StartRunRequest


class _FakeSubscription:
    def on(self, event, listener):
        pass

    def off(self, event, listener):
        pass

    def close(self):
        pass


class _FakeConnectionManager:
    def ensure_client_id(self):
        return "client-1"

    def connect_if_needed(self):
        pass

    def subscribe(self, session_id):
        return _FakeSubscription()


class TestRunVersionPinning(unittest.TestCase):
    def setUp(self):
        self.posted_payloads = []

        def make_request(method, path, body=None):
            self.posted_payloads.append(body)
            return {"session_id": "session-1"}

        self.client = RunsClient(_FakeConnectionManager(), make_request)

    def test_dataclass_request_sends_workflow_version_range_when_set(self):
        """A semver range on the request must reach POST /run unchanged; the backend
        resolves it to the highest matching tagged release."""
        self.client.start(
            StartRunRequest(workflow_id="wf-1", run_input_variables={}, workflow_version="^1.2.0")
        )

        self.assertEqual(self.posted_payloads[0]["workflow_version"], "^1.2.0")
        self.assertNotIn("workflow_branch_id", self.posted_payloads[0])

    def test_dict_request_sends_workflow_branch_id_when_set(self):
        """Dict requests are passed through as-is, so a branch pin given as a dict key
        must reach POST /run just like the dataclass field does."""
        self.client.start(
            {"workflow_id": "wf-1", "run_input_variables": {}, "workflow_branch_id": "branch-uuid"}
        )

        self.assertEqual(self.posted_payloads[0]["workflow_branch_id"], "branch-uuid")
        self.assertNotIn("workflow_version", self.posted_payloads[0])

    def test_dataclass_request_without_pins_omits_both_pin_keys_from_payload(self):
        """asdict() serializes every field, including None ones. Backends without run
        version pinning reject unknown fields even when null, so unset pins must be
        dropped or every unpinned run would fail against them."""
        self.client.start(StartRunRequest(workflow_id="wf-1", run_input_variables={}))

        self.assertNotIn("workflow_version", self.posted_payloads[0])
        self.assertNotIn("workflow_branch_id", self.posted_payloads[0])

    def test_dict_request_with_explicit_none_pins_omits_both_pin_keys_from_payload(self):
        """A dict caller may set the pin keys to None explicitly; those must be dropped
        for the same reason as unset dataclass fields."""
        self.client.start(
            {
                "workflow_id": "wf-1",
                "run_input_variables": {},
                "workflow_version": None,
                "workflow_branch_id": None,
            }
        )

        self.assertNotIn("workflow_version", self.posted_payloads[0])
        self.assertNotIn("workflow_branch_id", self.posted_payloads[0])

    def test_unpinned_request_keeps_serializing_other_none_fields_as_before(self):
        """Only the pin keys are dropped; existing None-valued fields keep being sent so
        the payload for an unpinned run is unchanged from earlier SDK versions."""
        self.client.start(StartRunRequest(workflow_id="wf-1", run_input_variables={}))

        self.assertIn("dry_run", self.posted_payloads[0])
        self.assertIsNone(self.posted_payloads[0]["dry_run"])

    def test_setting_both_version_and_branch_pins_raises_before_any_request(self):
        """The backend accepts at most one pin and answers 400 otherwise; failing locally
        gives a clearer error and avoids a pointless request."""
        with self.assertRaises(ValueError):
            self.client.start(
                StartRunRequest(
                    workflow_id="wf-1",
                    run_input_variables={},
                    workflow_version="1.2.3",
                    workflow_branch_id="branch-uuid",
                )
            )
        with self.assertRaises(ValueError):
            self.client.start(
                {
                    "workflow_id": "wf-1",
                    "run_input_variables": {},
                    "workflow_version": "1.x",
                    "workflow_branch_id": "branch-uuid",
                }
            )

        self.assertEqual(self.posted_payloads, [])


if __name__ == "__main__":
    unittest.main()
