from __future__ import annotations

from typing import Callable, Dict, Set, Any


EventHandler = Callable[[Any], None]


class SimpleEventEmitter:
    def __init__(self) -> None:
        self._listeners: Dict[str, Set[EventHandler]] = {}

    def on(self, event: str, handler: EventHandler) -> Callable[[], None]:
        if event not in self._listeners:
            self._listeners[event] = set()
        self._listeners[event].add(handler)

        def off() -> None:
            s = self._listeners.get(event)
            if s and handler in s:
                s.remove(handler)

        return off

    def emit(self, event: str, payload: Any | None = None) -> None:
        handlers = self._listeners.get(event)
        if not handlers:
            return
        for h in list(handlers):
            try:
                h(payload)
            except Exception:
                # Swallow exceptions in user handlers to avoid breaking emitter
                pass

    def clear(self) -> None:
        self._listeners.clear()

