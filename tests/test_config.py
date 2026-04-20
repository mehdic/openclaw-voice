from __future__ import annotations

import textwrap

from openclaw_voice.app import config as config_module


def test_load_config_with_mock_yaml_files(tmp_path, monkeypatch):
    defaults_yaml = textwrap.dedent(
        """
        voice:
          default_agent: test-agent
          default_model: yaml-default-model
        server:
          web_port: 9000
          session_cookie_secure: false
        timeouts:
          gateway:
            connect: 11.0
            read: 22.0
            write: 33.0
            pool: 44.0
        commands:
          /help: Help text
        prompts:
          bootstrap_files: [bootstrap.md]
          dynamic_files: [dynamic.md]
        livekit:
          url: wss://yaml-livekit.example.test
        """
    )
    agents_yaml = textwrap.dedent(
        """
        agents:
          Test-Agent:
            display_name: YAML Agent
            emoji: Y
            language: fr
            voice:
              voice_id: yaml-voice
              model: eleven_flash_v2_5
            llm:
              model: yaml-agent-model
              models:
                primary: provider/primary
                fallbacks: [provider/fallback]
        users:
          Person@Example.com:
            agents: [test-agent]
            default: test-agent
        default_user:
          agents: [test-agent]
          default: test-agent
        """
    )

    (tmp_path / "defaults.yaml").write_text(defaults_yaml, encoding="utf-8")
    (tmp_path / "agents.yaml").write_text(agents_yaml, encoding="utf-8")

    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path)
    monkeypatch.setenv("WEB_PORT", "9999")
    monkeypatch.setenv("OPENCLAW_URL", "https://env-openclaw.example.test")
    monkeypatch.setenv("AUTHORIZED_EMAILS", "first@example.com, Second@example.com ")
    monkeypatch.setenv("AUTH_MODE", "google")

    cfg = config_module._load_config()

    assert "test-agent" in cfg.agents
    assert cfg.agents["test-agent"].display_name == "YAML Agent"
    assert cfg.users["person@example.com"].default == "test-agent"
    assert cfg.default_user.default == "test-agent"
    assert cfg.server.web_port == 9999
    assert cfg.server.session_cookie_secure is False
    assert cfg.timeouts.gateway.connect == 11.0
    assert cfg.prompts_bootstrap_files == ["bootstrap.md"]
    assert cfg.prompts_dynamic_files == ["dynamic.md"]
    assert cfg.livekit_url == "wss://yaml-livekit.example.test"
    assert cfg.openclaw_url == "https://env-openclaw.example.test"
    assert cfg.authorized_emails == {"first@example.com", "second@example.com"}
    assert cfg.auth_mode == "google"


def test_get_agent_config_falls_back_to_default(monkeypatch, test_config):
    monkeypatch.setattr(config_module, "get_config", lambda: test_config)

    agent = config_module.get_agent_config("missing-agent")

    assert agent.display_name == "Test Agent"


def test_get_user_config_falls_back_to_default_user(monkeypatch, test_config):
    monkeypatch.setattr(config_module, "get_config", lambda: test_config)

    user_cfg = config_module.get_user_config("missing@example.com")

    assert user_cfg.default == "test-agent"
    assert user_cfg.agents == ["test-agent"]


def test_get_allowed_models_returns_primary_and_fallbacks(monkeypatch, test_config):
    monkeypatch.setattr(config_module, "get_config", lambda: test_config)

    models = config_module.get_allowed_models("test-agent")

    assert models == [
        "openai/gpt-4.1-mini",
        "anthropic/claude-3-5-sonnet",
        "google/gemini-2.0-flash",
    ]


def test_normalize_agent_id():
    assert config_module._normalize_agent_id("  My-Agent  ") == "my-agent"


def test_authorized_emails_parsing_from_env(tmp_path, monkeypatch):
    (tmp_path / "defaults.yaml").write_text("{}", encoding="utf-8")
    (tmp_path / "agents.yaml").write_text("agents: {}", encoding="utf-8")

    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path)
    monkeypatch.setenv("AUTHORIZED_EMAILS", " One@example.com ,two@example.com,,")

    cfg = config_module._load_config()

    assert cfg.authorized_emails == {"one@example.com", "two@example.com"}


def test_auth_mode_defaults_to_demo(tmp_path, monkeypatch):
    (tmp_path / "defaults.yaml").write_text("{}", encoding="utf-8")
    (tmp_path / "agents.yaml").write_text("agents: {}", encoding="utf-8")

    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path)

    cfg = config_module._load_config()

    assert cfg.auth_mode == "demo"
