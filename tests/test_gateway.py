from __future__ import annotations

from openclaw_voice.openclaw import client as client_module


class DummyTimeout:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class DummyLLM:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def test_create_gateway_llm_constructs_correct_base_url(monkeypatch, test_config):
    monkeypatch.setattr(client_module, "get_config", lambda: test_config)
    monkeypatch.setattr(client_module.httpx, "Timeout", DummyTimeout)
    monkeypatch.setattr(client_module.openai, "LLM", DummyLLM)

    llm = client_module.create_gateway_llm("test-agent")

    assert llm.kwargs["base_url"] == "https://openclaw.example.test/v1"
    assert llm.kwargs["model"] == "openclaw/test-agent"


def test_create_gateway_llm_uses_model_override(monkeypatch, test_config):
    monkeypatch.setattr(client_module, "get_config", lambda: test_config)
    monkeypatch.setattr(client_module.httpx, "Timeout", DummyTimeout)
    monkeypatch.setattr(client_module.openai, "LLM", DummyLLM)

    llm = client_module.create_gateway_llm("test-agent", "override-model")

    assert llm.kwargs["extra_headers"] == {"x-openclaw-model": "override-model"}


def test_create_gateway_llm_falls_back_to_default_model(monkeypatch, test_config):
    monkeypatch.setattr(client_module, "get_config", lambda: test_config)
    monkeypatch.setattr(client_module.httpx, "Timeout", DummyTimeout)
    monkeypatch.setattr(client_module.openai, "LLM", DummyLLM)

    llm = client_module.create_gateway_llm("test-agent")

    assert llm.kwargs["extra_headers"] == {"x-openclaw-model": "gateway-default"}
    assert llm.kwargs["timeout"].kwargs == {
        "connect": 10.0,
        "read": 90.0,
        "write": 10.0,
        "pool": 10.0,
    }
