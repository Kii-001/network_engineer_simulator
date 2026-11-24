"""Event bus sederhana (publish/subscribe) agar modul tidak saling bergantung."""
from collections import defaultdict
from typing import Any, Callable


class EventManager:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[..., None]]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: Callable[..., None]) -> None:
        if handler not in self._handlers[event_name]:
            self._handlers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: Callable[..., None]) -> None:
        if handler in self._handlers[event_name]:
            self._handlers[event_name].remove(handler)

    def emit(self, event_name: str, **payload: Any) -> int:
        """Kirim event; mengembalikan jumlah handler yang dipanggil."""
        handlers = list(self._handlers.get(event_name, []))
        for handler in handlers:
            handler(**payload)
        return len(handlers)
