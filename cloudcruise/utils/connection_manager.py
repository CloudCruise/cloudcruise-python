from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, Optional, Set, Iterator

from .sse import open_sse, SSEHandlers, SSEConnection
from .events import SimpleEventEmitter
from .async_queue import AsyncEventQueue


def _is_final_event(event_type: Optional[str]) -> bool:
    return event_type in {"execution.success", "execution.failed", "execution.stopped"}


class SessionSubscription:
    def __init__(self, emitter: SimpleEventEmitter, queue: AsyncEventQueue[Dict[str, Any]], on_close: callable):
        self._emitter = emitter
        self._queue = queue
        self._on_close = on_close

    def on(self, event: str, handler):
        return self._emitter.on(event, handler)

    def close(self) -> None:
        try:
            self._queue.close()
        finally:
            self._on_close()

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        return iter(self._queue)


class _SessionChannel:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.emitter = SimpleEventEmitter()
        self.subscribers: Set[AsyncEventQueue[Dict[str, Any]]] = set()
        self.ended = False


class ConnectionManager:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._client_id: Optional[str] = None
        self._conn: Optional[SSEConnection] = None
        self._connecting = False
        self._connected = False
        self._reconnecting = False
        self._reconnect_delays = [1.0, 3.0, 10.0]
        self._sessions: Dict[str, _SessionChannel] = {}
        self._lock = threading.Lock()

    def ensure_client_id(self) -> str:
        if self._client_id:
            return self._client_id
        self._client_id = str(uuid.uuid4())
        return self._client_id

    def connect_if_needed(self) -> None:
        with self._lock:
            if self._connected or self._connecting:
                return
            if not self._client_id:
                self.ensure_client_id()
            self._open_mux_connection()

    def subscribe(self, session_id: str, stop_event: Optional[threading.Event] = None) -> SessionSubscription:
        # Kick off connection if not already
        try:
            self.connect_if_needed()
        except Exception:
            pass

        with self._lock:
            ch = self._sessions.get(session_id)
            if not ch:
                ch = _SessionChannel(session_id)
                self._sessions[session_id] = ch

            q: AsyncEventQueue[Dict[str, Any]] = AsyncEventQueue()
            ch.subscribers.add(q)

            def _on_close() -> None:
                with self._lock:
                    try:
                        q.close()
                    except Exception:
                        pass
                    ch.subscribers.discard(q)
                    if ch.subscribers.__len__() == 0 and ch.ended:
                        self._sessions.pop(session_id, None)

            return SessionSubscription(ch.emitter, q, _on_close)

    def _emit_all(self, event: str, payload: Any | None = None) -> None:
        for ch in list(self._sessions.values()):
            ch.emitter.emit(event, payload)

    def _open_mux_connection(self) -> None:
        if self._connecting or self._connected:
            return
        if not self._client_id:
            self.ensure_client_id()

        self._connecting = True
        url = f"{self._base_url}/run/clients/{self._client_id}/events"
        headers = {"cc-key": self._api_key}

        def on_open() -> None:
            with self._lock:
                self._connected = True
                self._connecting = False
            self._emit_all("open")

        def on_event(evt: Dict[str, Any]) -> None:
            # Expected events: {event: 'ping'| 'run.event', data: {...}}
            if evt.get("event") == "ping":
                self._emit_all("ping", evt)
                return
            if evt.get("event") == "run.event":
                raw_data = evt.get("data")
                data: Dict[str, Any] = {}
                if isinstance(raw_data, dict):
                    inner = raw_data.get("data")
                    if isinstance(inner, dict):
                        data = inner
                    else:
                        data = raw_data
                payload = data.get("payload") if isinstance(data, dict) else None
                session_id = None
                if isinstance(payload, dict):
                    val = payload.get("session_id") or payload.get("sessionId")
                    if isinstance(val, str):
                        session_id = val
                if session_id is None and isinstance(data, dict):
                    val = data.get("session_id") or data.get("sessionId")
                    if isinstance(val, str):
                        session_id = val
                if not session_id:
                    return
                ch = self._sessions.get(session_id)
                if not ch:
                    return
                msg = {"event": "run.event", "data": data}
                for q in list(ch.subscribers):
                    q.push(msg)
                ch.emitter.emit("run.event", msg)
                ev_type = data.get("event")
                if isinstance(ev_type, str) and _is_final_event(ev_type):
                    ch.ended = True
                    ch.emitter.emit("end", {"type": ev_type})
                    for q in list(ch.subscribers):
                        q.close()
                    ch.subscribers.clear()
                    # Remove channel
                    self._sessions.pop(session_id, None)

        def on_error(err: Exception) -> None:
            self._emit_all("error", err)
            with self._lock:
                if not self._reconnecting:
                    self._schedule_reconnect()

        def on_close() -> None:
            with self._lock:
                self._connected = False
                self._connecting = False
            self._emit_all("close")
            with self._lock:
                if not self._reconnecting:
                    self._schedule_reconnect()

        try:
            self._conn = open_sse(
                url,
                SSEHandlers(on_open=on_open, on_event=on_event, on_error=on_error, on_close=on_close),
                headers=headers,
            )
        except Exception:
            with self._lock:
                self._connected = False
                self._connecting = False
                if not self._reconnecting:
                    self._schedule_reconnect()

    def _schedule_reconnect(self) -> None:
        if self._reconnecting:
            return
        self._reconnecting = True

        def worker() -> None:
            for delay in self._reconnect_delays:
                # Notify listeners about reconnect attempt
                for ch in list(self._sessions.values()):
                    ch.emitter.emit("reconnect", {"attemptDelayMs": int(delay * 1000)})
                time.sleep(delay)
                try:
                    self._open_mux_connection()
                    if self._connected:
                        self._reconnecting = False
                        return
                except Exception:
                    pass
            # Give up; keep flag false so that new subscribe/connect can reattempt
            self._reconnecting = False

        t = threading.Thread(target=worker, name="cloudcruise-reconnect", daemon=True)
        t.start()
