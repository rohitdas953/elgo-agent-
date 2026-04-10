from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from telegram_bot.models import ProductInfo
from telegram_bot.search.models import PlatformResult

logger = logging.getLogger("agentscore.session")

SESSION_TTL_SECONDS = 600  # 10 minutes


class UserState(str, Enum):
    IDLE = "IDLE"
    AWAITING_SELECTION = "AWAITING_SELECTION"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"


class UserSession:
    """Per-user conversational state."""

    __slots__ = (
        "user_id",
        "state",
        "identified_product",
        "search_results",
        "selected_option",
        "created_at",
        "updated_at",
        "_lock",
    )

    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        self.state = UserState.IDLE
        self.identified_product: ProductInfo | None = None
        self.search_results: list[PlatformResult] = []
        self.selected_option: PlatformResult | None = None
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)
        self._lock = asyncio.Lock()

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)

    def is_expired(self) -> bool:
        elapsed = (datetime.now(UTC) - self.updated_at).total_seconds()
        return elapsed > SESSION_TTL_SECONDS

    def reset(self) -> None:
        self.state = UserState.IDLE
        self.identified_product = None
        self.search_results = []
        self.selected_option = None
        self.touch()

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "state": self.state.value,
            "identified_product": (
                self.identified_product.model_dump() if self.identified_product else None
            ),
            "search_results_count": len(self.search_results),
            "selected_option": (
                self.selected_option.model_dump() if self.selected_option else None
            ),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class SessionManager:
    """Thread-safe in-memory session store with auto-expiry."""

    def __init__(self) -> None:
        self._sessions: dict[int, UserSession] = {}
        self._global_lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task[None] | None = None

    async def start_cleanup_loop(self) -> None:
        """Launch periodic expired-session reaper."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._reaper())

    async def stop_cleanup_loop(self) -> None:
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def get(self, user_id: int) -> UserSession:
        """Get or create a session for *user_id*."""
        async with self._global_lock:
            session = self._sessions.get(user_id)
            if session is None or session.is_expired():
                session = UserSession(user_id)
                self._sessions[user_id] = session
                logger.info("session_created user_id=%s", user_id)
            session.touch()
            return session

    async def remove(self, user_id: int) -> None:
        async with self._global_lock:
            self._sessions.pop(user_id, None)

    async def _reaper(self) -> None:
        """Runs every 60 s, drops expired sessions."""
        while True:
            await asyncio.sleep(60)
            async with self._global_lock:
                expired = [
                    uid for uid, s in self._sessions.items() if s.is_expired()
                ]
                for uid in expired:
                    del self._sessions[uid]
                if expired:
                    logger.info("sessions_reaped count=%d", len(expired))


# Module-level singleton
session_manager = SessionManager()
