import threading
import unittest

from cloudcruise.runs.client import RunsClient
from cloudcruise.runs.types import (
    FlattenedRunEvent,
    RunResult,
    VideoUrl,
    WebhookEvent,
    WebhookReplayResponse,
)
from cloudcruise.utils.events import SimpleEventEmitter
from cloudcruise.workflows.client import WorkflowsClient
from cloudcruise.workflows.types import (
    InputValidationError,
    Workflow,
    WorkflowInputSchema,
    WorkflowMetadata,
)


class TestWorkflowDataclassResponses(unittest.TestCase):
    def test_get_all_workflows_returns_dataclasses_and_ignores_unknown_fields(self):
        client = WorkflowsClient(
            lambda *_: [
                {
                    "id": "wf-1",
                    "name": "Workflow",
                    "description": None,
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                    "workspace_id": "workspace-1",
                    "created_by": "user-1",
                    "enable_popup_handling": True,
                    "enable_xpath_recovery": True,
                    "enable_error_code_generation": False,
                    "enable_service_unavailable_recovery": False,
                    "enable_action_timing_recovery": True,
                    "future_field": "ignored",
                }
            ]
        )

        workflows = client.get_all_workflows()

        self.assertIsInstance(workflows[0], Workflow)
        self.assertEqual(workflows[0].id, "wf-1")
        self.assertFalse(hasattr(workflows[0], "future_field"))

    def test_get_workflow_metadata_returns_nested_dataclass(self):
        client = WorkflowsClient(
            lambda *_: {
                "metadata": {
                    "input_schema": {
                        "type": "object",
                        "properties": {"url": {"type": "string"}},
                        "required": ["url"],
                        "additionalProperties": False,
                    }
                }
            }
        )

        metadata = client.get_workflow_metadata("wf-1")

        self.assertIsInstance(metadata, WorkflowMetadata)
        self.assertIsInstance(metadata.input_schema, WorkflowInputSchema)
        self.assertEqual(metadata.input_schema.required, ["url"])


class _FakeSubscription:
    def __init__(self):
        self.emitter = SimpleEventEmitter()

    def on(self, event, handler):
        return self.emitter.on(event, handler)

    def close(self):
        pass

    def emit_terminal_event(self, payload=None):
        self.emitter.emit(
            "run.event",
            {
                "event": "run.event",
                "data": {
                    "event": "execution.success",
                    "payload": payload or {},
                    "timestamp": 1,
                    "expires_at": 2,
                },
            },
        )


class _FakeConnectionManager:
    def __init__(self):
        self.subscription = _FakeSubscription()

    def ensure_client_id(self):
        return "client-1"

    def connect_if_needed(self):
        pass

    def subscribe(self, session_id):
        return self.subscription


class _RequiredInputWorkflows:
    def validate_workflow_input(self, workflow_id, payload):
        if "url" not in payload:
            raise InputValidationError("missing required: url", ["url"])


class TestRunDataclassResponses(unittest.TestCase):
    def test_get_results_returns_nested_dataclasses(self):
        client = RunsClient(
            _FakeConnectionManager(),
            lambda *_: {
                "session_id": "session-1",
                "workflow_id": "wf-1",
                "status": "execution.success",
                "input_variables": {"url": "https://example.com"},
                "data": {"ok": True},
                "video_urls": [
                    {
                        "timestamp": "now",
                        "session_id": "session-1",
                        "signed_screen_recording_url": "https://example.com/video",
                        "signed_screen_recording_url_expires": "later",
                    }
                ],
                "unknown": "ignored",
            },
        )

        result = client.get_results("session-1")

        self.assertIsInstance(result, RunResult)
        self.assertEqual(result.status, "execution.success")
        self.assertEqual(result.workflow_id, "wf-1")
        self.assertIsInstance(result.video_urls[0], VideoUrl)
        self.assertFalse(hasattr(result, "unknown"))

    def test_replay_webhooks_returns_nested_dataclasses(self):
        client = RunsClient(
            _FakeConnectionManager(),
            lambda *_: {
                "status": "ok",
                "info": "replayed",
                "nr_success": 1,
                "nr_failed": 0,
                "webhook_events": [
                    {"success": True, "response": "200", "error": ""},
                ],
            },
        )

        replay = client.replay_webhooks("session-1")

        self.assertIsInstance(replay, WebhookReplayResponse)
        self.assertIsInstance(replay.webhook_events[0], WebhookEvent)

    def test_wait_returns_run_result_dataclass(self):
        conn = _FakeConnectionManager()

        def make_request(method, path, body=None):
            if method == "GET":
                return {
                    "session_id": "session-1",
                    "status": "execution.success",
                    "input_variables": {},
                    "data": {"done": True},
                }
            raise AssertionError(f"unexpected request: {method} {path}")

        client = RunsClient(conn, make_request)
        handle = client.subscribe_to_session("session-1")
        result_holder = {}
        waiter = threading.Thread(
            target=lambda: result_holder.setdefault("result", handle.wait())
        )
        waiter.start()

        conn.subscription.emit_terminal_event()
        waiter.join(timeout=1)

        self.assertFalse(waiter.is_alive())
        self.assertIsInstance(result_holder["result"], RunResult)
        self.assertEqual(result_holder["result"].data["done"], True)

    def test_run_event_callbacks_receive_flattened_dataclasses(self):
        conn = _FakeConnectionManager()
        client = RunsClient(conn, lambda *_: {})
        handle = client.subscribe_to_session("session-1")
        events = []

        handle.on("run.event", events.append)

        conn.subscription.emit_terminal_event({"session_id": "session-1", "status": "ok"})

        self.assertIsInstance(events[0], FlattenedRunEvent)
        self.assertEqual(events[0].type, "execution.success")
        self.assertEqual(events[0].payload["status"], "ok")
        self.assertEqual(events[0].timestamp, 1)
        self.assertEqual(events[0].expires_at, 2)
        self.assertEqual(events[0].raw["event"], "run.event")

    def test_start_dict_without_inputs_normalizes_to_empty_dict_before_validation(self):
        client = RunsClient(
            _FakeConnectionManager(),
            lambda *_: {"session_id": "session-1"},
            _RequiredInputWorkflows(),
        )

        with self.assertRaises(InputValidationError) as ctx:
            client.start({"workflow_id": "wf-1"})

        self.assertEqual(ctx.exception.missingRequired, ["url"])

    def test_start_dict_requires_workflow_id(self):
        client = RunsClient(_FakeConnectionManager(), lambda *_: {"session_id": "session-1"})

        with self.assertRaisesRegex(ValueError, "workflow_id is required"):
            client.start({})

    def test_start_dict_requires_dict_run_input_variables(self):
        client = RunsClient(_FakeConnectionManager(), lambda *_: {"session_id": "session-1"})

        with self.assertRaisesRegex(ValueError, "run_input_variables must be a dict"):
            client.start({"workflow_id": "wf-1", "run_input_variables": ["not", "a", "dict"]})

    def test_start_dict_sends_normalized_empty_inputs(self):
        captured = {}

        def make_request(method, path, body=None):
            captured["body"] = body
            return {"session_id": "session-1"}

        client = RunsClient(_FakeConnectionManager(), make_request)

        client.start({"workflow_id": "wf-1"})

        self.assertEqual(captured["body"]["run_input_variables"], {})


if __name__ == "__main__":
    unittest.main()
