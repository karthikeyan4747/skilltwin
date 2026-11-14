"""Small in-process TTL cache (bounded, monotonic clock)."""

import time
from collections import OrderedDict
from collections.abc import Hashable
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: float, max_items: int = 512) -> None:
        self.ttl = ttl_seconds
        self.max_items = max_items
        self._items: OrderedDict[Hashable, tuple[float, Any]] = OrderedDict()

    def get(self, key: Hashable) -> Any | None:
        """Cached value, or None if missing or expired."""
        entry = self._items.get(key)
        if entry is None:
            return None
        expires, value = entry
        if expires < time.monotonic():
            del self._items[key]
            return None
        self._items.move_to_end(key)
        return value

    def set(self, key: Hashable, value: Any) -> None:
        """Store a value, evicting the least recently used entry when full."""
        self._items[key] = (time.monotonic() + self.ttl, value)
        self._items.move_to_end(key)
        while len(self._items) > self.max_items:
            self._items.popitem(last=False)
