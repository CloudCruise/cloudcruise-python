from __future__ import annotations

import threading
import time
import sys
from typing import Any, Callable, Dict, Iterator, Optional


def _default_recovery_submit_error_log(operation: str, err: BaseException) -> None:
    """Default error reporter for the recovery helpers. Writes to stderr so
    submission failures surface in customer logs even if no on_error callback
    is provided. The runtime SimpleEventEmitter swallows all handler
    exceptions, so without this default a 4xx/5xx from /new_input_variables
    would vanish into the void."""
    try:
        sys.stderr.write(
            f"[CloudCruise SDK] {operation} failed during recovery: "
            f"{type(err).__name__}: {err}\n"
        )
    except Exception:
        pass


def _verbose_log(operation: str, message: str) -> None:
    """Helper for `verbose=True` mode on the recovery helpers. Writes a
    structured line to stderr so customers can watch the recovery loop
    end-to-end without instrumenting their own decider."""
    try:
        sys.stderr.write(f"[CloudCruise SDK verbose] {operation}: {message}\n")
    except Exception:
        pass

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
    FlattenedRunEvent,
    RunEventEnvelope,
    LiveViewConnection,
)
from ..utils.types import to_dataclass

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

    def start(self, request: StartRunRequest | Dict[str, Any], options: Optional[RunStreamOptions] = None) -> RunHandle:
        if isinstance(request, dict):
            workflow_id = request.get("workflow_id")
            if not workflow_id:
                raise ValueError("workflow_id is required to start a run")
            run_input_variables = request.get("run_input_variables") or {}
            if not isinstance(run_input_variables, dict):
                raise ValueError("run_input_variables must be a dict when provided")
            request = {
                **request,
                "workflow_id": workflow_id,
                "run_input_variables": run_input_variables,
            }
        else:
            workflow_id = request.workflow_id
            run_input_variables = request.run_input_variables or {}
            request.run_input_variables = run_input_variables
        if self._workflows is not None:
            # Validate input variables proactively
            self._workflows.validate_workflow_input(workflow_id, run_input_variables)

        client_id = self._connection_manager.ensure_client_id()
        self._connection_manager.connect_if_needed()
        if isinstance(request, dict):
            request["client_id"] = client_id
        else:
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

        def flatten_event(msg: RunEventEnvelope) -> FlattenedRunEvent:
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
            Into a FlattenedRunEvent with attribute access.
            """
            data = msg.get("data", {})
            return FlattenedRunEvent(
                type=data.get("event") or "",
                payload=data.get("payload", {}),
                timestamp=data.get("timestamp"),
                expires_at=data.get("expires_at"),
                raw=msg,
            )

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
                event_type = flattened.type

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

    def submit_modal_action(self, session_id: str, action_id: str) -> None:
        """
        Respond to an execution.input_required event whose reason is
        "non_dismissible_popup" by picking one of the CTA buttons surfaced in
        popup_context.available_actions. The backend dispatches a synthetic
        click on the chosen button and resumes the workflow.

        Only valid while the session is waiting for input. The backing
        endpoint returns 400 if the wait already expired (the workspace
        setting input_required_timeout_seconds, default 15s, max 300s).

        Args:
            session_id: The session waiting for input.
            action_id: One of the ids in popup_context.available_actions.
        """
        path = f"/run/{session_id}/new_input_variables"
        self._make_request("POST", path, {"modal_action": action_id})

    def submit_input_variables(self, session_id: str, input_variables: Dict[str, Any]) -> None:
        """
        Respond to an execution.input_required event whose reason is one of
        "input_required", "incorrect_form_input", or "multiple_matching_results"
        by supplying the corrected/required input variables. The backend
        resumes the workflow from the appropriate recovery node with the new
        values substituted in.

        Mutually exclusive with submit_modal_action on the same session.

        Args:
            session_id: The session waiting for input.
            input_variables: Mapping of variable name to new value.
        """
        path = f"/run/{session_id}/new_input_variables"
        self._make_request("POST", path, {"input_variables": input_variables})

    def get_results(self, session_id: str) -> RunResult:
        path = f"/run/{session_id}"
        response = self._make_request("GET", path)
        return to_dataclass(response, RunResult)

    def get_live_view_connection(self, session_id: str) -> LiveViewConnection:
        """
        Fetch a fresh live-view connection (viewer URL + auth token) for
        watching an active session's browser stream. The auth token is
        single-use, so reopening a previously used viewer link will fail —
        call this again to mint a new one instead.

        Only works while the session is still active; raises once the
        session has ended.
        """
        path = f"/live/sessions/{session_id}/connection"
        response = self._make_request("GET", path)
        return LiveViewConnection(
            url=response["url"],
            session_id=response.get("sessionId", session_id),
            auth_token=response["authToken"],
        )

    def interrupt(self, session_id: str) -> None:
        path = f"/run/{session_id}/interrupt"
        self._make_request("POST", path)

    def replay_webhooks(self, session_id: str) -> WebhookReplayResponse:
        path = f"/webhooks/{session_id}/replay"
        response = self._make_request("POST", path)
        return to_dataclass(response, WebhookReplayResponse)

    def on_popup_decision_required(
        self,
        handle: RunHandle,
        decider: Callable[[Dict[str, Any]], str],
        on_error: Optional[Callable[[BaseException], None]] = None,
        verbose: bool = False,
    ) -> Callable[[], None]:
        """
        Register a listener that auto-responds ONLY to non-dismissible modal
        input_required events (reason == "non_dismissible_popup"). The decider
        receives the popup_context dict and must return one of the action ids
        in popup_context.available_actions.

        This is the recommended ergonomic for the non-dismissible recovery path.
        Other input_required reasons (incorrect_form_input, etc.) are routed
        to on_input_variables_required and ignored here.

        The SDK never picks an action on its own. The customer's decider IS
        the decision point. If decider raises, the listener swallows it and
        skips submission; the backend's input wait will time out naturally.

        Args:
            handle: The RunHandle returned by client.runs.start(...).
            decider: Callable taking the popup_context dict, returns action_id.

        Returns:
            Unsubscribe callable.

        Example:
            def decider(ctx):
                # ctx["retry"]["attempt"] available for branching
                if "duplicate" in ctx["error_description"].lower():
                    return next(a["id"] for a in ctx["available_actions"]
                                if "proceed" in a["label"].lower())
                return ctx["available_actions"][0]["id"]

            handle = client.runs.start(request)
            client.runs.on_popup_decision_required(handle, decider)
            result = handle.wait()
        """
        if verbose:
            _verbose_log("on_popup_decision_required", "listener registered")

        def listener(event: Any) -> None:
            if isinstance(event, dict):
                data = event.get("data")
                payload = (data or {}).get("payload") if isinstance(data, dict) else event.get("payload")
            else:
                data = getattr(event, "data", None)
                payload = (
                    getattr(data, "payload", None)
                    if data is not None
                    else getattr(event, "payload", None)
                )
            if not isinstance(payload, dict):
                return
            if payload.get("reason") != "non_dismissible_popup":
                if verbose:
                    _verbose_log(
                        "on_popup_decision_required",
                        f"skipping reason={payload.get('reason')!r}",
                    )
                return
            popup_ctx = payload.get("popup_context")
            if not isinstance(popup_ctx, dict):
                return

            if verbose:
                attempt = (popup_ctx.get("retry") or {}).get("attempt")
                actions = [a.get("id") for a in popup_ctx.get("available_actions", [])]
                _verbose_log(
                    "on_popup_decision_required",
                    f"event received attempt={attempt} actions={actions}",
                )

            try:
                action_id = decider(popup_ctx)
            except Exception as e:
                if verbose:
                    _verbose_log("on_popup_decision_required", f"decider raised: {e}")
                return
            if not isinstance(action_id, str) or not action_id:
                if verbose:
                    _verbose_log(
                        "on_popup_decision_required",
                        f"decider returned non-string/empty ({action_id!r}); skipping",
                    )
                return

            session_id = payload.get("session_id") or handle.sessionId
            if verbose:
                _verbose_log(
                    "on_popup_decision_required",
                    f"submitting modal_action={action_id!r} for session={session_id}",
                )
            try:
                self.submit_modal_action(session_id, action_id)
                if verbose:
                    _verbose_log(
                        "on_popup_decision_required",
                        f"submit ok for action={action_id!r}",
                    )
            except BaseException as e:
                reporter = on_error or (
                    lambda err: _default_recovery_submit_error_log(
                        "submit_modal_action", err
                    )
                )
                try:
                    reporter(e)
                except Exception:
                    pass

        unsubscribe = handle.on("execution.input_required", listener)
        if callable(unsubscribe):
            return unsubscribe
        return lambda: None

    def on_input_variables_required(
        self,
        handle: RunHandle,
        decider: Callable[[Dict[str, Any]], Dict[str, Any]],
        on_error: Optional[Callable[[BaseException], None]] = None,
        verbose: bool = False,
    ) -> Callable[[], None]:
        """
        Register a listener that auto-responds ONLY to workflow-variable
        input_required events (reason in {"input_required",
        "incorrect_form_input", "multiple_matching_results"}). The decider
        receives the full payload dict and must return the input_variables
        dict to submit.

        This is the counterpart to on_popup_decision_required. Modal events
        (reason == "non_dismissible_popup") are routed there and ignored here.

        The decider receives the entire payload (including reason,
        input_variables hint, screenshot_url, etc.) so it can branch its
        response based on which variable-recovery sub-reason fired.

        Args:
            handle: The RunHandle returned by client.runs.start(...).
            decider: Callable taking the payload dict, returns input_variables.

        Returns:
            Unsubscribe callable.

        Example:
            def decider(payload):
                if payload["reason"] == "incorrect_form_input":
                    return {"USERNAME": prompt_operator_for_username()}
                if payload["reason"] == "input_required":
                    return {"MEMBER_ID": lookup_member_id()}
                return {}

            handle = client.runs.start(request)
            client.runs.on_input_variables_required(handle, decider)
            result = handle.wait()
        """
        VARIABLE_REASONS = {"input_required", "incorrect_form_input", "multiple_matching_results"}

        if verbose:
            _verbose_log("on_input_variables_required", "listener registered")

        def listener(event: Any) -> None:
            # Tolerate both SSE envelope (data.payload) and flat (payload).
            if isinstance(event, dict):
                data = event.get("data")
                payload = (data or {}).get("payload") if isinstance(data, dict) else event.get("payload")
            else:
                data = getattr(event, "data", None)
                payload = (
                    getattr(data, "payload", None)
                    if data is not None
                    else getattr(event, "payload", None)
                )
            if not isinstance(payload, dict):
                return
            reason = payload.get("reason")
            if reason not in VARIABLE_REASONS:
                if verbose:
                    _verbose_log(
                        "on_input_variables_required",
                        f"skipping reason={reason!r}",
                    )
                return

            if verbose:
                _verbose_log(
                    "on_input_variables_required",
                    f"event received reason={reason!r}",
                )

            try:
                input_vars = decider(payload)
            except Exception as e:
                if verbose:
                    _verbose_log(
                        "on_input_variables_required", f"decider raised: {e}"
                    )
                return
            if not isinstance(input_vars, dict) or isinstance(input_vars, list):
                if verbose:
                    _verbose_log(
                        "on_input_variables_required",
                        f"decider returned non-dict ({type(input_vars).__name__}); skipping",
                    )
                return

            session_id = payload.get("session_id") or handle.sessionId
            if verbose:
                _verbose_log(
                    "on_input_variables_required",
                    f"submitting input_variables keys={list(input_vars.keys())} for session={session_id}",
                )
            try:
                self.submit_input_variables(session_id, input_vars)
                if verbose:
                    _verbose_log("on_input_variables_required", "submit ok")
            except BaseException as e:
                reporter = on_error or (
                    lambda err: _default_recovery_submit_error_log(
                        "submit_input_variables", err
                    )
                )
                try:
                    reporter(e)
                except Exception:
                    pass

        unsubscribe = handle.on("execution.input_required", listener)
        if callable(unsubscribe):
            return unsubscribe
        return lambda: None
