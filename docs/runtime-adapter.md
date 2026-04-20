# Runtime Adapter Contract

`openclaw_voice.runtime.base.RuntimeAdapter` is the narrow interface between OpenClaw Voice and any real-time voice transport/runtime backend.

## Required Interface

Every runtime adapter must implement:

- `async connect(room_name: str, agent_id: str, metadata: dict[str, Any]) -> None`
- `async disconnect() -> None`
- `is_connected() -> bool`
- `name` property returning the backend identifier, such as `"livekit"` or `"pipecat"`

The intent is to keep the boundary small:

- `room_name` identifies the voice session to join or attach to
- `agent_id` identifies the OpenClaw agent configuration to load
- `metadata` carries backend-specific session context, model overrides, or other runtime hints

## Registration Mechanism

Adapters are registered through `openclaw_voice.runtime.registry`.

- `register(name, adapter_cls)` stores an adapter class under a runtime name
- `get(name)` returns the registered adapter class or raises `KeyError`
- `available()` lists registered runtime names

The current LiveKit backend registers itself automatically in `src/openclaw_voice/runtime/livekit/__init__.py`:

```python
from ..registry import register
from .worker import LiveKitAdapter

register("livekit", LiveKitAdapter)
```

That keeps registration close to the backend package instead of scattering it in app startup code.

## How To Add A New Backend

1. Create a new package, for example `src/openclaw_voice/runtime/pipecat/`.
2. Add an adapter class that subclasses `RuntimeAdapter`.
3. Implement `connect`, `disconnect`, `is_connected`, and `name`.
4. Keep backend-specific SDK details inside that package.
5. Export the adapter from the backend package `__init__.py`.
6. Register it in that same `__init__.py` with `register("<name>", AdapterClass)`.
7. Add tests for registry behavior and backend-specific connection lifecycle behavior.
8. Wire app startup or config-based backend selection later when the product is ready for multiple runtimes.

## Pipecat Skeleton

```python
"""Pipecat runtime adapter for OpenClaw Voice."""

from __future__ import annotations

from typing import Any

from ..base import RuntimeAdapter
from ..registry import register


class PipecatAdapter(RuntimeAdapter):
    def __init__(self) -> None:
        self._connected = False

    @property
    def name(self) -> str:
        return "pipecat"

    async def connect(self, room_name: str, agent_id: str, metadata: dict[str, Any]) -> None:
        # Initialize Pipecat transport/session objects here.
        self._connected = True

    async def disconnect(self) -> None:
        # Shut down Pipecat resources here.
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected


register("pipecat", PipecatAdapter)
```

## What Is Still Hardcoded

The MVP is not fully runtime-agnostic yet.

- The process entrypoint still starts the LiveKit worker directly.
- Session startup still assumes the LiveKit worker model and `JobContext`.
- Room naming and participant metadata parsing remain implemented in the LiveKit backend.
- Config does not yet expose a runtime selector.

## What Is Now Pluggable

- The abstract runtime contract is explicit and testable.
- Runtime implementations can be discovered by name through the registry.
- LiveKit is now represented as a concrete adapter class instead of only module-level worker functions.
- A second backend can be added without rewriting the registry or changing the adapter contract.
