from __future__ import annotations

import threading
from typing import Generic, Iterator, Optional, TypeVar


T = TypeVar("T")


class AsyncEventQueue(Generic[T]):
    """
    A thread-cooperative queue that supports iteration until closed.
    """

    def __init__(self) -> None:
        self._items: list[T] = []
        self._closed = False
        self._cv = threading.Condition()

    def push(self, item: T) -> None:
        with self._cv:
            if self._closed:
                return
            self._items.append(item)
            self._cv.notify()

    def close(self) -> None:
        with self._cv:
            if self._closed:
                return
            self._closed = True
            self._cv.notify_all()

    def __iter__(self) -> Iterator[T]:
        while True:
            with self._cv:
                while not self._items and not self._closed:
                    self._cv.wait()
                if self._items:
                    item = self._items.pop(0)
                    yield item
                elif self._closed:
                    return

