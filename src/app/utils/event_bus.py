from __future__ import annotations

import queue
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class AppEvent:
    type: str
    message: str | None = None
    level: str = "INFO"
    value: float | None = None
    data: dict | None = field(default=None)


class EventBus:
    def __init__(self, root):
        self._queue: queue.Queue[AppEvent] = queue.Queue()
        self._root = root
        self._subscribers: list[Callable[[AppEvent], None]] = []

    def subscribe(self, handler):
        self._subscribers.append(handler)

    def unsubscribe(self, handler):
        self._subscribers = [s for s in self._subscribers if s != handler]

    def emit(self, event: AppEvent) -> None:
        self._queue.put(event)  # safe from any thread

    def start(self) -> None:
        def _poll():
            try:
                while True:
                    ev = self._queue.get_nowait()
                    for sub in list(self._subscribers):
                        try:
                            sub(ev)
                        except Exception as e:
                            print(f"[EventBus] {e}")
            except queue.Empty:
                pass
            finally:
                self._root.after(30, _poll)

        _poll()
