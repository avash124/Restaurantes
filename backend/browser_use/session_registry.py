"""
Global registry of active Browser Use session IDs.

Agents register their session ID as soon as the remote session is created,
and unregister when done.  The FastAPI lifespan calls stop_all_sessions()
on shutdown so in-flight sessions are terminated on the browser-use.com API
rather than running indefinitely after the process exits.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from browser_use_sdk.v3.resources.sessions import AsyncSessions

logger = logging.getLogger(__name__)

# Thread-safe via GIL; asyncio.Lock not needed for simple set ops in one event loop.
_active: set[str] = set()


def register(session_id: str) -> None:
    _active.add(session_id)
    logger.debug("[registry] registered session %s  (total active: %d)", session_id, len(_active))


def unregister(session_id: str) -> None:
    _active.discard(session_id)
    logger.debug("[registry] unregistered session %s  (total active: %d)", session_id, len(_active))


def active_session_ids() -> frozenset[str]:
    return frozenset(_active)


async def stop_all_sessions(sessions: "AsyncSessions") -> None:
    """Stop every registered session.  Called during FastAPI lifespan shutdown."""
    ids = list(_active)
    if not ids:
        return

    logger.info("[registry] stopping %d active browser-use session(s) on shutdown...", len(ids))

    async def _stop_one(tid: str) -> None:
        try:
            await sessions.stop(tid)
            logger.info("[registry] stopped session %s", tid)
        except Exception as exc:
            logger.warning("[registry] could not stop session %s: %s", tid, exc)
        finally:
            _active.discard(tid)

    await asyncio.gather(*(_stop_one(tid) for tid in ids), return_exceptions=True)
