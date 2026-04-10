"""In-memory activity log for real-time frontend display.

Every significant backend event (vision, search, order, payment, bot command)
is appended here. The frontend polls GET /api/activity-log to show a live feed.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Any

MAX_LOG_ENTRIES = 200


@dataclass
class ActivityEntry:
    ts: float = field(default_factory=time.time)
    event: str = ""           # e.g. "vision", "search", "order", "payment", "bot_cmd"
    level: str = "info"       # info | warn | error | success
    source: str = "system"    # system | telegram | algorand | vision | search | order
    title: str = ""
    detail: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["ts_iso"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.ts))
        return d


class ActivityLog:
    def __init__(self, maxlen: int = MAX_LOG_ENTRIES):
        self._entries: deque[ActivityEntry] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    async def push(self, entry: ActivityEntry) -> None:
        with self._lock:
            self._entries.append(entry)

    def push_sync(self, entry: ActivityEntry) -> None:
        with self._lock:
            self._entries.append(entry)

    async def get_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._entries)
        return [e.to_dict() for e in items[-limit:]][::-1]  # newest first


# Singleton
activity_log = ActivityLog()


def log_event(
    event: str,
    title: str,
    detail: str = "",
    level: str = "info",
    source: str = "system",
    **meta: Any,
) -> None:
    """Fire-and-forget sync logging helper."""
    entry = ActivityEntry(
        event=event,
        level=level,
        source=source,
        title=title,
        detail=detail,
        meta=meta,
    )
    activity_log.push_sync(entry)
