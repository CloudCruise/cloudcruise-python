from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from cloudcruise.runs.client import RunsClient

CONTRACT = json.loads((Path(__file__).resolve().parent / "contract" / "api-contract.json").read_text())


def make_client(response=None) -> RunsClient:
    client = RunsClient.__new__(RunsClient)
    client._make_request = MagicMock(return_value=response)  # type: ignore[attr-defined]
    return client


class TestRespondToDecision(unittest.TestCase):
    def test_posts_decision_id_and_the_answer_to_the_decision_answer_endpoint_the_api_serves(self):
        client = make_client({"status": "accepted", "decision_id": "dec-1"})
        result = client.respond_to_decision(
            "sess-1", "dec-1", {"values": {"choice": "keep"}, "text": "Use the newest"}
        )
        client._make_request.assert_called_once_with(  # type: ignore[attr-defined]
            "POST",
            "/run/sess-1/decision/respond",
            {"decision_id": "dec-1", "values": {"choice": "keep"}, "text": "Use the newest"},
        )
        self.assertIn("/run/{session_id}/decision/respond", CONTRACT["paths"])
        self.assertEqual(result, {"status": "accepted", "decision_id": "dec-1"})

    def test_sends_a_directive_alone_and_every_body_key_is_one_the_api_accepts(self):
        client = make_client({"status": "accepted", "decision_id": "dec-2"})
        client.respond_to_decision("sess-2", "dec-2", {"directive": "requeue"})
        body = client._make_request.call_args.args[2]  # type: ignore[attr-defined]
        self.assertEqual(body, {"decision_id": "dec-2", "directive": "requeue"})
        accepted = CONTRACT["decision_respond_request"]["properties"]
        for key in body:
            self.assertIn(key, accepted)


if __name__ == "__main__":
    unittest.main()
