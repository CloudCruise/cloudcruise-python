from __future__ import annotations

import threading
import time
from typing import Any, Dict, Iterator, Optional

from ..utils.async_queue import AsyncEventQueue
from ..utils.events import SimpleEventEmitter
from ..utils.connection_manager import ConnectionManager, SessionSubscription
from ..workflows.client import WorkflowsClient
from .types import (
    StartRunRequest,
    UserInteractionData,
    RunResult,
    WebhookReplayResponse,
    RunStreamOptions,
    SseMessage,
    RunHandle,
)

class RunsClient:
    def __init__(
        self,
        connection_manager: ConnectionManager,
        make_request,
        workflows: Optional[WorkflowsClient] = None,
    ) -> None:
        self._make_request = make_request
        self._workflows = workflows
        self._connection_manager = connection_manager

    def start(self, request: StartRunRequest, options: Optional[RunStreamOptions] = None) -> RunHandle:
        if self._workflows is not None:
            # Validate input variables proactively
            self._workflows.validate_workflow_input(request.workflow_id, request.run_input_variables)

        client_id = self._connection_manager.ensure_client_id()
        self._connection_manager.connect_if_needed()
        request.client_id = client_id
        from dataclasses import is_dataclass, asdict
        payload = asdict(request) if is_dataclass(request) else (
            dict(request) if isinstance(request, dict) else request.__dict__
        )
        resp = self._make_request("POST", "/run", payload)
        session_id: Optional[str]
        if isinstance(resp, dict):
            session_id = resp.get("session_id") or resp.get("sessionId")
        else:
            session_id = getattr(resp, "session_id", None) or getattr(resp, "sessionId", None)
        if not session_id:
            raise RuntimeError("CloudCruise start run response did not include session_id")
        return self.subscribe_to_session(session_id, options)

    def subscribe_to_session(self, session_id: str, options: Optional[RunStreamOptions] = None) -> RunHandle:
        emitter = SimpleEventEmitter()
        stream: AsyncEventQueue[SseMessage] = AsyncEventQueue()

        ended = False
        closed = False
        sub: Optional[SessionSubscription] = None

        reconnect_enabled = True if options is None or options.reconnect_enabled is None else options.reconnect_enabled
        reconnect_delays = options.reconnect_delays if options and options.reconnect_delays else [1.0, 3.0, 10.0]

        def is_terminal(status: Optional[str]) -> bool:
            return status in {"execution.success", "execution.failed", "execution.stopped"}

        def flatten_event(msg: Dict[str, Any]) -> Dict[str, Any]:
            """
            Flatten the nested SSE event structure for better UX.
            Transforms:
              {
                'event': 'run.event',
                'data': {
                  'event': 'execution.start',
                  'payload': {...},
                  'timestamp': ...
                }
              }
            Into:
              {
                'type': 'execution.start',
                'payload': {...},
                'timestamp': ...,
                '_raw': {...}  # original message
              }
            """
            data = msg.get("data", {})
            flattened = {
                "type": data.get("event"),
                "payload": data.get("payload", {}),
                "timestamp": data.get("timestamp"),
                "expires_at": data.get("expires_at"),
                "_raw": msg,
            }
            return flattened

        def emit(event: str, payload: Any | None = None) -> None:
            emitter.emit(event, payload)
            if event in ("run.event", "ping"):
                emitter.emit("message", payload)

        def end_and_cleanup(status: str) -> None:
            nonlocal ended, closed, sub
            if ended:
                return
            ended = True
            closed = True
            try:
                if sub is not None:
                    sub.close()
            except Exception:
                pass
            emit("end", {"type": status})
            stream.close()
            emitter.clear()

        def connect() -> None:
            nonlocal sub
            sub = self._connection_manager.subscribe(session_id)
            s = sub
            s.on("open", lambda _=None: emit("open"))
            s.on("ping", lambda evt: emit("ping", evt))

            def on_run_event(msg: Any) -> None:
                nonlocal ended
                m = msg  # expected dict
                if not isinstance(m, dict) or m.get("event") != "run.event":
                    return

                # Flatten the event for better UX
                flattened = flatten_event(m)
                event_type = flattened.get("type")

                # Push original message to stream for iteration
                stream.push(m)  # type: ignore

                # Emit flattened event to 'run.event' listeners
                emit("run.event", flattened)

                # Also emit to type-specific listeners (e.g., 'execution.start')
                # This matches the JS SDK behavior and provides better DX
                if event_type and isinstance(event_type, str):
                    try:
                        emit(event_type, flattened)
                    except Exception:
                        pass  # Ignore errors in type-specific emission

                if isinstance(event_type, str) and is_terminal(event_type):
                    end_and_cleanup(event_type)

            s.on("run.event", on_run_event)
            s.on("error", lambda err: _on_error(err))
            s.on("reconnect", lambda e: emit("reconnect", e))
            s.on("end", lambda e: end_and_cleanup((e or {}).get("type", "execution.stopped")))

        def _on_error(err: Any) -> None:
            emit("error", err)
            if not reconnect_enabled or ended or closed:
                return
            def worker():
                for base in reconnect_delays:
                    if ended or closed:
                        return
                    time.sleep(base)
                    if ended or closed:
                        return
                    try:
                        snapshot = self.get_results(session_id)
                        status = snapshot.get("status") if isinstance(snapshot, dict) else snapshot.status
                        if isinstance(status, str) and is_terminal(status):
                            end_and_cleanup(status)
                            return
                    except Exception:
                        pass
                    emit("reconnect", {"attemptDelayMs": int(base * 1000)})
                    return  # Connection manager handles reconnect of mux
            t = threading.Thread(target=worker, name="cloudcruise-run-reconnect", daemon=True)
            t.start()

        connect()

        client = self

        class _RunHandle:
            sessionId = session_id

            def on(self, event: str, handler):
                return emitter.on(event, handler)

            def wait(self) -> RunResult:
                # Block until end and then fetch results
                if ended:
                    return client.get_results(session_id)

                done = threading.Event()
                result_container: Dict[str, Any] = {}

                def on_end(_):
                    try:
                        result_container["result"] = client.get_results(session_id)
                    finally:
                        done.set()

                def on_error(err):
                    result_container["error"] = err
                    done.set()

                off_end = self.on("end", on_end)
                off_err = self.on("error", on_error)
                done.wait()
                try:
                    if "error" in result_container:
                        err = result_container["error"]
                        raise err if isinstance(err, Exception) else RuntimeError(f"SSE error: {err}")
                    return result_container["result"]
                finally:
                    try:
                        off_end()
                    except Exception:
                        pass
                    try:
                        off_err()
                    except Exception:
                        pass

            def close(self) -> None:
                nonlocal closed, sub
                closed = True
                try:
                    if sub is not None:
                        sub.close()
                except Exception:
                    pass
                stream.close()
                emitter.clear()

            def __iter__(self) -> Iterator[SseMessage]:
                for msg in stream:
                    yield msg

        return _RunHandle()

    def submit_user_interaction(self, session_id: str, data: UserInteractionData) -> None:
        path = f"/run/{session_id}/user_interaction"
        self._make_request("POST", path, data)

    def get_results(self, session_id: str) -> RunResult:
        path = f"/run/{session_id}"
        return self._make_request("GET", path)

    def interrupt(self, session_id: str) -> None:
        path = f"/run/{session_id}/interrupt"
        self._make_request("POST", path)

    def replay_webhooks(self, session_id: str) -> WebhookReplayResponse:
        path = f"/webhooks/{session_id}/replay"
        return self._make_request("POST", path)
