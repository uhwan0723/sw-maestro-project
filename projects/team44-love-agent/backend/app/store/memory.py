from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.schemas.consultation import ConsultationState, utc_now_iso


T = TypeVar("T")
StateMutator = Callable[[ConsultationState], T | Awaitable[T]]


class ConsultationNotFoundError(KeyError):
    """Raised when a consultation_id is not present in the in-memory store."""


class MemoryStore:
    """consultation_id-scoped in-memory state store.

    The store allows many consultations to run concurrently. Locks are scoped per
    consultation_id, so only concurrent writes to the same consultation are
    serialized.
    """

    def __init__(self) -> None:
        self._states: dict[str, ConsultationState] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._store_lock = asyncio.Lock()

    async def create(self, state: ConsultationState) -> bool:
        async with self._store_lock:
            if state.consultation_id in self._states:
                return False
            self._states[state.consultation_id] = state
            self._locks[state.consultation_id] = asyncio.Lock()
            return True

    async def get(self, consultation_id: str) -> ConsultationState | None:
        lock = await self._lock_for_existing(consultation_id)
        if lock is None:
            return None
        async with lock:
            return self._states[consultation_id].model_copy(deep=True)

    async def mutate(
        self,
        consultation_id: str,
        mutator: StateMutator[T],
        *,
        touch_updated_at: bool = True,
    ) -> tuple[ConsultationState, T]:
        lock = await self._lock_for_existing(consultation_id)
        if lock is None:
            raise ConsultationNotFoundError(consultation_id)

        async with lock:
            state = self._states[consultation_id]
            result = mutator(state)
            if inspect.isawaitable(result):
                result = await result
            if touch_updated_at:
                state.updated_at = utc_now_iso()
            return state.model_copy(deep=True), result

    async def _lock_for_existing(self, consultation_id: str) -> asyncio.Lock | None:
        async with self._store_lock:
            return self._locks.get(consultation_id)
