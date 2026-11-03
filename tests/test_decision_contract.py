import json
import unittest
from pathlib import Path
from typing import get_args

from cloudcruise import (
    AgentDecisionAnsweredPayload,
    AgentDecisionRequestedPayload,
    DecisionWebhookAnswer,
    DecisionWebhookAnsweredVia,
    DecisionWebhookDirective,
    DecisionWebhookField,
    DecisionWebhookOption,
    DecisionWebhookOutcome,
    EventType,
)

CONTRACT = json.loads((Path(__file__).resolve().parent / "contract" / "api-contract.json").read_text())
REQUESTED = CONTRACT["decision_requested"]
ANSWERED = CONTRACT["decision_answered"]
RESPOND = CONTRACT["decision_respond_request"]


class TestDecisionRequiredMatchesTheApiContract(unittest.TestCase):
    def assert_typed_dict_matches_schema(self, typed_dict, schema):
        keys = typed_dict.__required_keys__ | typed_dict.__optional_keys__
        self.assertEqual(sorted(keys), sorted(schema["properties"]), f"{typed_dict.__name__} keys")
        self.assertEqual(
            sorted(typed_dict.__required_keys__),
            sorted(schema.get("required", [])),
            f"{typed_dict.__name__} required keys",
        )

    def test_both_decision_required_events_are_in_event_type_and_subscribable_in_the_api_and_input_required_is_gone_from_both(self):
        sdk_events = get_args(EventType)
        for event in ("agent.decision_requested", "agent.decision_answered"):
            self.assertIn(event, sdk_events)
            self.assertIn(event, CONTRACT["subscribable_events"])
            self.assertIn(event, CONTRACT["webhooks"])
        self.assertNotIn("execution.input_required", sdk_events)
        self.assertNotIn("execution.input_required", CONTRACT["subscribable_events"])

    def test_the_api_serves_the_decision_answer_endpoint_and_no_longer_serves_new_input_variables_which_the_removed_runs_helpers_called(self):
        self.assertIn("/run/{session_id}/decision/respond", CONTRACT["paths"])
        self.assertNotIn("/run/{session_id}/new_input_variables", CONTRACT["paths"])

    def test_agent_decision_requested_payload_has_the_same_keys_and_required_keys_as_the_api_payload(self):
        self.assert_typed_dict_matches_schema(AgentDecisionRequestedPayload, REQUESTED)

    def test_decision_field_and_option_match_the_api_field_and_option_objects_key_for_key(self):
        field = REQUESTED["properties"]["fields"]["items"]
        self.assert_typed_dict_matches_schema(DecisionWebhookField, field)
        self.assert_typed_dict_matches_schema(DecisionWebhookOption, field["properties"]["options"]["items"])

    def test_agent_decision_answered_payload_and_its_answer_match_the_api_payload_and_answer_object(self):
        self.assert_typed_dict_matches_schema(AgentDecisionAnsweredPayload, ANSWERED)
        self.assert_typed_dict_matches_schema(DecisionWebhookAnswer, ANSWERED["properties"]["answer"])

    def test_outcome_answered_via_and_directive_literals_list_exactly_the_values_the_api_sends(self):
        properties = ANSWERED["properties"]
        self.assertEqual(sorted(get_args(DecisionWebhookOutcome)), sorted(properties["outcome"]["enum"]))
        self.assertEqual(sorted(get_args(DecisionWebhookAnsweredVia)), sorted(properties["answered_via"]["enum"]))
        self.assertEqual(
            sorted(get_args(DecisionWebhookDirective)),
            sorted(properties["answer"]["properties"]["directive"]["enum"]),
        )

    def test_an_answer_built_from_decision_webhook_answer_plus_decision_id_is_exactly_the_body_the_api_answer_endpoint_accepts(self):
        self.assertEqual(RESPOND["required"], ["decision_id"])
        self.assertEqual(
            sorted(key for key in RESPOND["properties"] if key != "decision_id"),
            sorted(DecisionWebhookAnswer.__optional_keys__ | DecisionWebhookAnswer.__required_keys__),
        )
        self.assertEqual(sorted(get_args(DecisionWebhookDirective)), sorted(RESPOND["properties"]["directive"]["enum"]))


if __name__ == "__main__":
    unittest.main()
