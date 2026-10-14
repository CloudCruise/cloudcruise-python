"""
Tests for submit_decision, which answers a DECISION_REQUIRED popup by option
label and optionally saves the choice for auto-apply on future runs.

Mirrors the mocked-client style of tests/test_modal_action.py.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from cloudcruise.runs.client import RunsClient


def make_client() -> RunsClient:
    client = RunsClient.__new__(RunsClient)
    client._make_request = MagicMock(return_value=None)  # type: ignore[attr-defined]
    return client


def test_submit_decision_posts_correct_shape():
    client = make_client()
    client.submit_decision("sess-123", "Reschedule")
    client._make_request.assert_called_once_with(  # type: ignore[attr-defined]
        "POST",
        "/run/sess-123/new_input_variables",
        {"chosen_option": "Reschedule", "save_decision": False},
    )


def test_submit_decision_sets_save_decision_true():
    client = make_client()
    client.submit_decision("sess-456", "Reschedule", save=True)
    client._make_request.assert_called_once_with(  # type: ignore[attr-defined]
        "POST",
        "/run/sess-456/new_input_variables",
        {"chosen_option": "Reschedule", "save_decision": True},
    )


def test_submit_decision_and_input_variables_use_different_bodies():
    client = make_client()
    client.submit_decision("sess-1", "Yes")
    client.submit_input_variables("sess-1", {"MEMBER_ID": "ABC"})
    assert client._make_request.call_count == 2  # type: ignore[attr-defined]
    first_body = client._make_request.call_args_list[0][0][2]  # type: ignore[attr-defined]
    second_body = client._make_request.call_args_list[1][0][2]  # type: ignore[attr-defined]
    assert "chosen_option" in first_body and "input_variables" not in first_body
    assert "input_variables" in second_body and "chosen_option" not in second_body
