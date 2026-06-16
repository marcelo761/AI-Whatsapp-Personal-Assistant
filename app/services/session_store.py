import asyncio
from collections import OrderedDict
from typing import Any


class SessionStore:
    def __init__(self, max_history: int, dedup_size: int = 5000) -> None:
        self._max_history = max_history
        self._history: dict[str, list[dict[str, str]]] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._processed_ids: OrderedDict[str, None] = OrderedDict()
        self._dedup_size = dedup_size
        self._global_lock = asyncio.Lock()

    async def get_lock(self, session_key: str) -> asyncio.Lock:
        async with self._global_lock:
            if session_key not in self._locks:
                self._locks[session_key] = asyncio.Lock()
            return self._locks[session_key]

    def is_duplicate(self, message_id: str) -> bool:
        if not message_id:
            return False
        return message_id in self._processed_ids

    def mark_processed(self, message_id: str) -> None:
        if not message_id:
            return
        self._processed_ids[message_id] = None
        while len(self._processed_ids) > self._dedup_size:
            self._processed_ids.popitem(last=False)

    def get_history(self, session_key: str) -> list[dict[str, str]]:
        return list(self._history.get(session_key, []))

    def append_message(self, session_key: str, role: str, content: str) -> None:
        history = self._history.setdefault(session_key, [])
        history.append({"role": role, "content": content})
        self._history[session_key] = history[-self._max_history :]

    def clear_history(self, session_key: str) -> None:
        self._history.pop(session_key, None)

    def stats(self) -> dict[str, Any]:
        return {
            "active_sessions": len(self._history),
            "processed_messages": len(self._processed_ids),
        }
