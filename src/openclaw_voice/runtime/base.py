"""Abstract runtime adapter contract for OpenClaw Voice."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class RuntimeAdapter(ABC):
    """Interface that all voice runtime backends must implement."""

    @abstractmethod
    async def connect(self, room_name: str, agent_id: str, metadata: dict[str, Any]) -> None:
        """Connect to a voice session."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect and clean up the session."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Return whether the adapter is currently connected."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the runtime backend name (e.g. livekit, pipecat)."""
