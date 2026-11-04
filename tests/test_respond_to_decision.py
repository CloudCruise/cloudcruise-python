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


class TestGetPendingDecision(unittest.TestCase):
    def test_reads_the_runs_pending_decision_and_returns_the_api_response_unchanged(self):
        response = {
            "decision": {
                "decision_id": "dec-1",
                "answer_by": "2026-11-04T20:00:00.000Z",
                "question": "Which record should be kept?",
                "context": "Two matching records",
                "fields": [
                    {"id": "choice", "label": "Record", "type": "single_choice", "options": [{"id": "keep", "label": "Keep"}]}
                ],
                "free_text": True,
                "respond_url": "https://api.example.test/run/sess-1/decision/respond",
            },
            "answered_decision_id": None,
        }
        client = make_client(response)
        result = client.get_pending_decision("sess-1")
        client._make_request.assert_called_once_with("GET", "/run/sess-1/decision/pending")  # type: ignore[attr-defined]
        self.assertEqual(result, response)

    def test_passes_through_a_run_with_nothing_pending_and_the_id_of_an_answered_decision(self):
        client = make_client({"decision": None, "answered_decision_id": "dec-1"})
        self.assertEqual(
            client.get_pending_decision("sess-1"), {"decision": None, "answered_decision_id": "dec-1"}
        )


if __name__ == "__main__":
    unittest.main()
