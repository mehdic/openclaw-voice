from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

SUPPORT_DIR = Path(__file__).resolve().parent / "_support"
if str(SUPPORT_DIR) not in sys.path:
    sys.path.insert(0, str(SUPPORT_DIR))

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _install_google_stubs() -> None:
    google_module = types.ModuleType("google")
    google_auth_module = types.ModuleType("google.auth")
    google_auth_transport_module = types.ModuleType("google.auth.transport")
    google_auth_requests_module = types.ModuleType("google.auth.transport.requests")
    google_oauth2_module = types.ModuleType("google.oauth2")
    google_id_token_module = types.ModuleType("google.oauth2.id_token")

    class Request:
        pass

    def verify_oauth2_token(*_args, **_kwargs):
        return {}

    google_auth_requests_module.Request = Request
    google_id_token_module.verify_oauth2_token = verify_oauth2_token

    google_module.auth = google_auth_module
    google_module.oauth2 = google_oauth2_module
    google_auth_module.transport = google_auth_transport_module
    google_auth_transport_module.requests = google_auth_requests_module
    google_oauth2_module.id_token = google_id_token_module

    sys.modules["google"] = google_module
    sys.modules["google.auth"] = google_auth_module
    sys.modules["google.auth.transport"] = google_auth_transport_module
    sys.modules["google.auth.transport.requests"] = google_auth_requests_module
    sys.modules["google.oauth2"] = google_oauth2_module
    sys.modules["google.oauth2.id_token"] = google_id_token_module


def _install_faster_whisper_stub() -> None:
    faster_whisper_module = types.ModuleType("faster_whisper")

    class WhisperModel:
        def __init__(self, *_args, **_kwargs):
            pass

        def transcribe(self, *_args, **_kwargs):
            return [], types.SimpleNamespace(language_probability=1.0)

    faster_whisper_module.WhisperModel = WhisperModel
    sys.modules["faster_whisper"] = faster_whisper_module


def _install_livekit_stubs() -> None:
    livekit_module = types.ModuleType("livekit")
    livekit_api_module = types.ModuleType("livekit.api")
    livekit_agents_module = types.ModuleType("livekit.agents")
    livekit_agents_stt_module = types.ModuleType("livekit.agents.stt")
    livekit_agents_types_module = types.ModuleType("livekit.agents.types")
    livekit_agents_utils_module = types.ModuleType("livekit.agents.utils")
    livekit_agents_voice_module = types.ModuleType("livekit.agents.voice")
    livekit_agents_voice_turn_module = types.ModuleType("livekit.agents.voice.turn")
    livekit_plugins_module = types.ModuleType("livekit.plugins")
    livekit_plugins_openai_module = types.ModuleType("livekit.plugins.openai")
    livekit_plugins_elevenlabs_module = types.ModuleType("livekit.plugins.elevenlabs")
    livekit_plugins_silero_module = types.ModuleType("livekit.plugins.silero")
    livekit_rtc_module = types.ModuleType("livekit.rtc")

    class VideoGrants:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class AccessToken:
        def __init__(self, api_key: str, api_secret: str):
            self.api_key = api_key
            self.api_secret = api_secret
            self.identity = ""
            self.name = ""
            self.grants = None
            self.metadata = ""

        def with_identity(self, identity: str):
            self.identity = identity
            return self

        def with_name(self, name: str):
            self.name = name
            return self

        def with_grants(self, grants):
            self.grants = grants
            return self

        def with_metadata(self, metadata: str):
            self.metadata = metadata
            return self

        def to_jwt(self) -> str:
            return f"jwt:{self.identity}"

    class Agent:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class AgentSession:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def start(self, **kwargs):
            self.start_kwargs = kwargs

    class AgentServer:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def rtc_session(self):
            def decorator(func):
                return func

            return decorator

    class STT:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class STTCapabilities:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class TurnHandlingOptions:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class DummyLLM:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class VoiceSettings:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class TTS:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class DummyVAD:
        @staticmethod
        def load():
            return "vad"

    class AudioBuffer:
        pass

    class APIConnectOptions:
        pass

    NOT_GIVEN = object()

    def run_app(*_args, **_kwargs):
        return None

    livekit_api_module.AccessToken = AccessToken
    livekit_api_module.VideoGrants = VideoGrants

    livekit_agents_module.Agent = Agent
    livekit_agents_module.AgentServer = AgentServer
    livekit_agents_module.AgentSession = AgentSession
    livekit_agents_module.JobContext = object
    livekit_agents_module.cli = types.SimpleNamespace(run_app=run_app)
    livekit_agents_module.stt = livekit_agents_stt_module

    livekit_agents_stt_module.STT = STT
    livekit_agents_stt_module.STTCapabilities = STTCapabilities

    livekit_agents_types_module.APIConnectOptions = APIConnectOptions
    livekit_agents_types_module.DEFAULT_API_CONNECT_OPTIONS = APIConnectOptions()
    livekit_agents_types_module.NOT_GIVEN = NOT_GIVEN
    livekit_agents_types_module.NotGivenOr = object

    livekit_agents_utils_module.AudioBuffer = AudioBuffer

    livekit_agents_voice_turn_module.TurnHandlingOptions = TurnHandlingOptions

    livekit_plugins_openai_module.LLM = DummyLLM
    livekit_plugins_elevenlabs_module.TTS = TTS
    livekit_plugins_elevenlabs_module.VoiceSettings = VoiceSettings
    livekit_plugins_silero_module.VAD = DummyVAD

    livekit_plugins_module.openai = livekit_plugins_openai_module
    livekit_plugins_module.elevenlabs = livekit_plugins_elevenlabs_module
    livekit_plugins_module.silero = livekit_plugins_silero_module

    livekit_module.api = livekit_api_module
    livekit_module.agents = livekit_agents_module
    livekit_module.plugins = livekit_plugins_module
    livekit_module.rtc = livekit_rtc_module

    sys.modules["livekit"] = livekit_module
    sys.modules["livekit.api"] = livekit_api_module
    sys.modules["livekit.agents"] = livekit_agents_module
    sys.modules["livekit.agents.stt"] = livekit_agents_stt_module
    sys.modules["livekit.agents.types"] = livekit_agents_types_module
    sys.modules["livekit.agents.utils"] = livekit_agents_utils_module
    sys.modules["livekit.agents.voice"] = livekit_agents_voice_module
    sys.modules["livekit.agents.voice.turn"] = livekit_agents_voice_turn_module
    sys.modules["livekit.plugins"] = livekit_plugins_module
    sys.modules["livekit.plugins.openai"] = livekit_plugins_openai_module
    sys.modules["livekit.plugins.elevenlabs"] = livekit_plugins_elevenlabs_module
    sys.modules["livekit.plugins.silero"] = livekit_plugins_silero_module
    sys.modules["livekit.rtc"] = livekit_rtc_module


_install_google_stubs()
_install_faster_whisper_stub()
_install_livekit_stubs()

from openclaw_voice.app import auth as auth_module
from openclaw_voice.app import config as config_module
from openclaw_voice.app import routes as routes_module
from openclaw_voice.app import server as server_module


@pytest.fixture(autouse=True)
def clear_config_cache():
    cache_clear = getattr(config_module.get_config, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()
    yield
    cache_clear = getattr(config_module.get_config, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()


@pytest.fixture(autouse=True)
def clean_config_env(monkeypatch: pytest.MonkeyPatch):
    for key in (
        "AUTH_MODE",
        "AUTHORIZED_EMAILS",
        "ELEVEN_API_KEY",
        "GOOGLE_CLIENT_ID",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
        "LIVEKIT_URL",
        "OPENAI_API_KEY",
        "OPENCLAW_TOKEN",
        "OPENCLAW_URL",
        "SESSION_SECRET",
        "WEB_PORT",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def mock_agents():
    return {
        "test-agent": config_module.AgentConfig(
            display_name="Test Agent",
            emoji="T",
            language="en",
            voice=config_module.VoiceConfig(
                voice_id="voice-123",
                model="eleven_turbo_v2_5",
            ),
            llm=config_module.LLMConfig(
                model="gateway-default",
                models=config_module.LLMModels(
                    primary="openai/gpt-4.1-mini",
                    fallbacks=["anthropic/claude-3-5-sonnet", "google/gemini-2.0-flash"],
                ),
            ),
        )
    }


@pytest.fixture
def test_config(mock_agents):
    return config_module.AppConfig(
        agents=mock_agents,
        users={
            "allowed@example.com": config_module.UserAccess(
                agents=["test-agent"],
                default="test-agent",
            )
        },
        default_user=config_module.UserAccess(
            agents=["test-agent"],
            default="test-agent",
        ),
        voice=config_module.VoiceDefaults(
            default_model="gateway-default",
            default_agent="test-agent",
        ),
        livekit_url="wss://livekit.example.test",
        livekit_api_key="livekit-key",
        livekit_api_secret="livekit-secret",
        openclaw_url="https://openclaw.example.test/",
        openclaw_token="openclaw-token",
        authorized_emails={"allowed@example.com"},
        session_secret="test-session-secret",
        auth_mode="demo",
        server=config_module.ServerConfig(
            web_port=7890,
            session_cookie_secure=False,
        ),
    )


@pytest.fixture
def test_app(monkeypatch: pytest.MonkeyPatch, test_config):
    for module in (config_module, auth_module, routes_module, server_module):
        monkeypatch.setattr(module, "get_config", lambda cfg=test_config: cfg)

    app = server_module.create_app()
    app.config.update(TESTING=True)
    return app


@pytest.fixture
def client(test_app):
    return test_app.test_client()
