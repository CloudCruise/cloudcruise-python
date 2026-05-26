"""
Tests for the non-dismissible modal recovery flow (execution.input_required
with popup_context, plus the submit_modal_action API + auto_handle_modals
helper).

Mirrors the unit-test style of tests/test_webhook.py: pure object construction
plus a small mocked HTTP client to verify the submit endpoint shape.
"""
from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from cloudcruise.events.types import (
    AvailableAction,
    PopupContext,
    PopupRetry,
    ExecutionInputRequiredPayload,
)
from cloudcruise.runs.client import RunsClient


def make_client() -> RunsClient:
    """Construct a RunsClient with the network layer mocked out."""
    client = RunsClient.__new__(RunsClient)
    client._make_request = MagicMock(return_value=None)  # type: ignore[attr-defined]
    return client


def test_popup_context_typeddict_shape():
    """PopupContext, AvailableAction, PopupRetry compose as expected."""
    ctx: PopupContext = {
        "error_description": "Duplicate patient warning blocks Save & Bill",
        "error_sub_type": "NON_DISMISSIBLE",
        "full_url": "https://demo.cloudcruise.com/ecw-encounter-multistep",
        "available_actions": [
            {"id": "proceed_with_selected_patient", "label": "Proceed with Selected Patient"},
            {"id": "cancel", "label": "Cancel"},
        ],
        "retry": {"attempt": 1, "max_attempts": 3},
    }
    assert ctx["retry"]["attempt"] == 1
    assert len(ctx["available_actions"]) == 2
    assert ctx["available_actions"][0]["id"] == "proceed_with_selected_patient"


def test_input_required_payload_with_popup_context():
    """ExecutionInputRequiredPayload carries reason + nested popup_context."""
    payload: ExecutionInputRequiredPayload = {
        "session_id": "sess-abc",
        "input_variables": {},
        "screenshot_url": None,
        "reason": "non_dismissible_popup",
        "popup_context": {
            "error_description": "Modal blocks click",
            "error_sub_type": "NON_DISMISSIBLE",
            "full_url": "https://example.com",
            "available_actions": [{"id": "yes", "label": "Yes"}],
            "retry": {"attempt": 1, "max_attempts": 3},
        },
    }
    assert payload["reason"] == "non_dismissible_popup"
    assert payload["popup_context"]["available_actions"][0]["id"] == "yes"


def test_input_required_payload_without_popup_context():
    """When reason != non_dismissible_popup, popup_context is omitted."""
    payload: ExecutionInputRequiredPayload = {
        "session_id": "sess-xyz",
        "input_variables": {},
        "screenshot_url": None,
        "reason": "incorrect_form_input",
    }
    assert payload["reason"] == "incorrect_form_input"
    assert "popup_context" not in payload


def test_submit_modal_action_posts_correct_shape():
    """submit_modal_action POSTs {modal_action: id} to the input variables endpoint."""
    client = make_client()
    client.submit_modal_action("sess-123", "proceed_with_selected_patient")
    client._make_request.assert_called_once_with(  # type: ignore[attr-defined]
        "POST",
        "/run/sess-123/new_input_variables",
        {"modal_action": "proceed_with_selected_patient"},
    )


def test_submit_input_variables_posts_correct_shape():
    """submit_input_variables POSTs {input_variables: dict} to the same endpoint."""
    client = make_client()
    client.submit_input_variables("sess-456", {"MEMBER_ID": "ABC123"})
    client._make_request.assert_called_once_with(  # type: ignore[attr-defined]
        "POST",
        "/run/sess-456/new_input_variables",
        {"input_variables": {"MEMBER_ID": "ABC123"}},
    )


def test_submit_modal_action_and_input_variables_use_different_bodies():
    """The two submit methods are XOR at the endpoint level; bodies do not mix."""
    client = make_client()
    client.submit_modal_action("sess-1", "yes")
    client.submit_input_variables("sess-1", {"X": 1})
    assert client._make_request.call_count == 2  # type: ignore[attr-defined]
    first_body = client._make_request.call_args_list[0][0][2]  # type: ignore[attr-defined]
    second_body = client._make_request.call_args_list[1][0][2]  # type: ignore[attr-defined]
    assert "modal_action" in first_body and "input_variables" not in first_body
    assert "input_variables" in second_body and "modal_action" not in second_body


def test_on_popup_decision_required_calls_decider_and_submits():
    """on_popup_decision_required wires a listener that calls decider(ctx) and submits."""
    client = make_client()

    # Capture the registered listener
    registered_listeners: Dict[str, Any] = {}

    class FakeHandle:
        sessionId = "sess-auto"

        def on(self, event: str, handler):
            registered_listeners[event] = handler
            return lambda: None  # unsubscribe

    handle = FakeHandle()
    decider_calls: List[Dict[str, Any]] = []

    def decider(ctx: Dict[str, Any]) -> str:
        decider_calls.append(ctx)
        return next(a["id"] for a in ctx["available_actions"] if "proceed" in a["label"].lower())

    unsubscribe = client.on_popup_decision_required(handle, decider)
    assert callable(unsubscribe)
    assert "execution.input_required" in registered_listeners

    # Simulate an event
    fake_event = {
        "payload": {
            "session_id": "sess-auto",
            "reason": "non_dismissible_popup",
            "popup_context": {
                "error_description": "Duplicate patient",
                "error_sub_type": "NON_DISMISSIBLE",
                "full_url": "https://example.com",
                "available_actions": [
                    {"id": "proceed_with_selected_patient", "label": "Proceed with Selected Patient"},
                    {"id": "cancel", "label": "Cancel"},
                ],
                "retry": {"attempt": 1, "max_attempts": 3},
            },
        }
    }
    registered_listeners["execution.input_required"](fake_event)

    assert len(decider_calls) == 1
    assert decider_calls[0]["error_description"] == "Duplicate patient"
    client._make_request.assert_called_once_with(  # type: ignore[attr-defined]
        "POST",
        "/run/sess-auto/new_input_variables",
        {"modal_action": "proceed_with_selected_patient"},
    )


def test_on_popup_decision_required_skips_non_modal_input_required():
    """Listener ignores input_required events whose reason isn't non_dismissible_popup."""
    client = make_client()
    listeners: Dict[str, Any] = {}

    class FakeHandle:
        sessionId = "sess-auto"

        def on(self, event: str, handler):
            listeners[event] = handler
            return lambda: None

    decider_calls: List[Dict[str, Any]] = []

    def decider(ctx):
        decider_calls.append(ctx)
        return "anything"

    client.on_popup_decision_required(FakeHandle(), decider)

    # Fire an incorrect_form_input event (popup_context absent)
    listeners["execution.input_required"](
        {"payload": {"session_id": "sess-auto", "reason": "incorrect_form_input", "input_variables": {}}}
    )

    assert decider_calls == []
    client._make_request.assert_not_called()  # type: ignore[attr-defined]


def test_on_popup_decision_required_swallows_decider_exceptions():
    """If decider raises, the listener does not propagate and does not submit."""
    client = make_client()
    listeners: Dict[str, Any] = {}

    class FakeHandle:
        sessionId = "sess-auto"

        def on(self, event: str, handler):
            listeners[event] = handler
            return lambda: None

    def decider(ctx):
        raise RuntimeError("operator picked nothing")

    client.on_popup_decision_required(FakeHandle(), decider)

    listeners["execution.input_required"](
        {
            "payload": {
                "session_id": "sess-auto",
                "reason": "non_dismissible_popup",
                "popup_context": {
                    "error_description": "Modal",
                    "error_sub_type": "NON_DISMISSIBLE",
                    "full_url": "https://x",
                    "available_actions": [{"id": "yes", "label": "Yes"}],
                    "retry": {"attempt": 1, "max_attempts": 3},
                },
            }
        }
    )

    client._make_request.assert_not_called()  # type: ignore[attr-defined]


def test_on_input_variables_required_routes_only_variable_reasons():
    """on_input_variables_required ignores modal events, fires only on variable reasons."""
    client = make_client()
    listeners: Dict[str, Any] = {}

    class FakeHandle:
        sessionId = "sess-var"

        def on(self, event, handler):
            listeners[event] = handler
            return lambda: None

    captured: List[Dict[str, Any]] = []

    def decider(payload: Dict[str, Any]) -> Dict[str, Any]:
        captured.append(payload)
        if payload.get("reason") == "incorrect_form_input":
            return {"USERNAME": "alice"}
        if payload.get("reason") == "input_required":
            return {"MEMBER_ID": "ABC123"}
        return {}

    client.on_input_variables_required(FakeHandle(), decider)

    # Modal event: should be ignored
    listeners["execution.input_required"](
        {"payload": {"session_id": "sess-var", "reason": "non_dismissible_popup",
                     "popup_context": {"available_actions": [{"id": "yes", "label": "Yes"}],
                                       "retry": {"attempt": 1, "max_attempts": 3},
                                       "error_description": "x", "error_sub_type": "NON_DISMISSIBLE", "full_url": "x"}}}
    )
    assert captured == []
    assert client._make_request.call_count == 0  # type: ignore[attr-defined]

    # incorrect_form_input event: should fire
    listeners["execution.input_required"](
        {"payload": {"session_id": "sess-var", "reason": "incorrect_form_input", "input_variables": {}}}
    )
    assert len(captured) == 1
    client._make_request.assert_called_with(  # type: ignore[attr-defined]
        "POST", "/run/sess-var/new_input_variables", {"input_variables": {"USERNAME": "alice"}}
    )

    # input_required event: should fire with different decider branch
    listeners["execution.input_required"](
        {"payload": {"session_id": "sess-var", "reason": "input_required", "input_variables": {}}}
    )
    assert len(captured) == 2
    last_call = client._make_request.call_args_list[-1]  # type: ignore[attr-defined]
    assert last_call[0][2] == {"input_variables": {"MEMBER_ID": "ABC123"}}


def test_two_handlers_can_coexist():
    """on_popup_decision_required and on_input_variables_required cleanly partition events."""
    client = make_client()
    listeners: List[Any] = []

    class FakeHandle:
        sessionId = "sess-both"

        def on(self, event, handler):
            listeners.append(handler)
            return lambda: None

    popup_calls = []
    var_calls = []

    client.on_popup_decision_required(FakeHandle(), lambda ctx: (popup_calls.append(ctx), "yes")[1])
    client.on_input_variables_required(FakeHandle(), lambda p: (var_calls.append(p), {"X": 1})[1])

    # Each call goes to BOTH listeners; each filters by reason internally.
    def fire(payload):
        for h in listeners:
            h({"payload": payload})

    fire({"session_id": "sess-both", "reason": "non_dismissible_popup",
          "popup_context": {"available_actions": [{"id": "yes", "label": "Yes"}],
                            "retry": {"attempt": 1, "max_attempts": 3},
                            "error_description": "x", "error_sub_type": "NON_DISMISSIBLE", "full_url": "x"}})
    fire({"session_id": "sess-both", "reason": "input_required", "input_variables": {}})

    assert len(popup_calls) == 1
    assert len(var_calls) == 1
    # Each handler submitted exactly once
    assert client._make_request.call_count == 2  # type: ignore[attr-defined]


def test_retry_attempt_visible_to_decider():
    """The decider can branch on retry.attempt to vary its choice."""
    client = make_client()
    listeners: Dict[str, Any] = {}

    class FakeHandle:
        sessionId = "sess-r"

        def on(self, event, handler):
            listeners[event] = handler
            return lambda: None

    def decider(ctx: Dict[str, Any]) -> str:
        # First try: prefer "yes". Retry: fall back to "no".
        if ctx["retry"]["attempt"] == 1:
            return "yes"
        return "no"

    client.on_popup_decision_required(FakeHandle(), decider)

    def fire(attempt: int):
        listeners["execution.input_required"](
            {
                "payload": {
                    "session_id": "sess-r",
                    "reason": "non_dismissible_popup",
                    "popup_context": {
                        "error_description": "x",
                        "error_sub_type": "NON_DISMISSIBLE",
                        "full_url": "https://x",
                        "available_actions": [{"id": "yes", "label": "Yes"}, {"id": "no", "label": "No"}],
                        "retry": {"attempt": attempt, "max_attempts": 3},
                    },
                }
            }
        )

    fire(1)
    fire(2)
    calls = client._make_request.call_args_list  # type: ignore[attr-defined]
    assert calls[0][0][2] == {"modal_action": "yes"}
    assert calls[1][0][2] == {"modal_action": "no"}
