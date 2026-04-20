"""ElevenLabs TTS provider helpers for OpenClaw Voice."""

from __future__ import annotations

from livekit.plugins import elevenlabs

from ...app.config import get_agent_config


def get_agent_voice_config(agent_id: str) -> dict:
    """Return voice configuration for an agent."""

    agent_cfg = get_agent_config(agent_id)
    return {
        "voice_id": agent_cfg.voice.voice_id,
        "model": agent_cfg.voice.model,
        "settings": agent_cfg.voice.settings.model_dump(),
    }


def get_tts_for_agent(agent_id: str) -> elevenlabs.TTS:
    """Create an ElevenLabs TTS instance for an agent."""

    voice_cfg = get_agent_voice_config(agent_id)
    settings = voice_cfg["settings"]
    return elevenlabs.TTS(
        voice_id=voice_cfg["voice_id"],
        model=voice_cfg["model"],
        voice_settings=elevenlabs.VoiceSettings(
            stability=settings["stability"],
            similarity_boost=settings["similarity_boost"],
            style=settings["style"],
        ),
    )
