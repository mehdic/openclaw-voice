from __future__ import annotations

import importlib
from typing import Any

import pytest

from openclaw_voice.runtime import registry
from openclaw_voice.runtime.base import RuntimeAdapter


class DummyAdapter(RuntimeAdapter):
    @property
    def name(self) -> str:
        return "dummy"

    async def connect(self, room_name: str, agent_id: str, metadata: dict[str, Any]) -> None:
        self.room_name = room_name
        self.agent_id = agent_id
        self.metadata = metadata

    async def disconnect(self) -> None:
        self.metadata = {}

    def is_connected(self) -> bool:
        return False


def test_register_and_get_work(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(registry, "_ADAPTERS", {})

    registry.register("dummy", DummyAdapter)

    assert registry.get("dummy") is DummyAdapter


def test_get_raises_key_error_for_unknown_runtime(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(registry, "_ADAPTERS", {})

    try:
        registry.get("missing")
    except KeyError as exc:
        assert str(exc) == '"Runtime \'missing\' not registered. Available: none"'
    else:
        raise AssertionError("Expected KeyError for unknown runtime")


def test_available_returns_registered_adapters(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(registry, "_ADAPTERS", {})

    registry.register("alpha", DummyAdapter)
    registry.register("beta", DummyAdapter)

    assert registry.available() == ["alpha", "beta"]


def test_livekit_adapter_is_auto_registered_on_import(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(registry, "_ADAPTERS", {})

    livekit_module = importlib.import_module("openclaw_voice.runtime.livekit")
    livekit_module = importlib.reload(livekit_module)

    assert registry.get("livekit") is livekit_module.LiveKitAdapter
    assert "livekit" in registry.available()
