from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Optional
import requests
import json
import re


SSEEvent = Dict[str, Any]


class SSEHandlers:
    def __init__(
        self,
        on_open: Optional[Callable[[], None]] = None,
        on_event: Optional[Callable[[SSEEvent], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
    ) -> None:
        self.on_open = on_open
        self.on_event = on_event
        self.on_error = on_error
        self.on_close = on_close


class SSEConnection:
    def __init__(self, closer: Callable[[], None]) -> None:
        self._close = closer

    def close(self) -> None:
        self._close()


def _parse_frame(frame: str) -> SSEEvent:
    event = "message"
    data = ""
    _id: Optional[str] = None
    for line in frame.splitlines():
        if not line or line.startswith(":"):
            continue
        idx = line.find(":")
        field = line if idx == -1 else line[:idx]
        value = "" if idx == -1 else line[idx + 1 :].lstrip()
        if field == "event":
            event = value
        elif field == "data":
            data = (data + "\n" + value) if data else value
        elif field == "id":
            _id = value
    parsed: Any
    try:
        parsed = None if data == "" else json.loads(data)
    except Exception:
        parsed = data
    return {"event": event, "data": parsed, "id": _id, "raw": frame}


def open_sse(
    url: str,
    handlers: SSEHandlers,
    headers: Optional[Dict[str, str]] = None,
    with_credentials: bool = False,
    stop_event: Optional[threading.Event] = None,
) -> SSEConnection:
    """
    Opens an SSE connection using requests streaming and parses frames.
    """
    session = requests.Session()
    req_headers = {
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
    }
    if headers:
        req_headers.update(headers)

    cancelled = threading.Event()
    if stop_event is None:
        stop_event = threading.Event()

    def run() -> None:
        try:
            with session.get(url, headers=req_headers, stream=True, timeout=60) as resp:
                if not resp.ok:
                    raise RuntimeError(f"SSE HTTP {resp.status_code}")
                if handlers.on_open:
                    try:
                        handlers.on_open()
                    except Exception:
                        pass
                buffer = ""
                for chunk in resp.iter_content(chunk_size=None):
                    if stop_event.is_set() or cancelled.is_set():
                        break
                    if not chunk:
                        continue
                    try:
                        text = chunk.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
                    parts = re.split(r"\r?\n\r?\n", buffer + text)
                    buffer = parts.pop() if parts else ""
                    for frame in parts:
                        evt = _parse_frame(frame)
                        if handlers.on_event:
                            try:
                                handlers.on_event(evt)
                            except Exception:
                                pass
        except Exception as e:
            if handlers.on_error:
                try:
                    handlers.on_error(e if isinstance(e, Exception) else Exception(str(e)))
                except Exception:
                    pass
        finally:
            if handlers.on_close:
                try:
                    handlers.on_close()
                except Exception:
                    pass

    thread = threading.Thread(target=run, name="cloudcruise-sse", daemon=True)
    thread.start()

    def _close() -> None:
        cancelled.set()
        stop_event.set()

    return SSEConnection(_close)
