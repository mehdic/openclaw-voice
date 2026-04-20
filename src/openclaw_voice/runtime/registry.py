"""Runtime adapter registry."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import RuntimeAdapter

_ADAPTERS: dict[str, type[RuntimeAdapter]] = {}


def register(name: str, adapter_cls: type[RuntimeAdapter]) -> None:
    _ADAPTERS[name] = adapter_cls


def get(name: str) -> type[RuntimeAdapter]:
    if name not in _ADAPTERS:
        available = ", ".join(_ADAPTERS.keys()) or "none"
        raise KeyError(f"Runtime {name!r} not registered. Available: {available}")
    return _ADAPTERS[name]


def available() -> list[str]:
    return list(_ADAPTERS.keys())
