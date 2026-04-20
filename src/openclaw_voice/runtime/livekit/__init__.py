"""LiveKit runtime adapter for OpenClaw Voice."""

from __future__ import annotations

from ..registry import register
from .worker import LiveKitAdapter

register("livekit", LiveKitAdapter)

__all__ = ["LiveKitAdapter"]
