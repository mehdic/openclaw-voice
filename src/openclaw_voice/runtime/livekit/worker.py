"""LiveKit worker runtime for OpenClaw Voice."""

from __future__ import annotations

import json
import logging
import signal
from typing import Any

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentSession
from livekit.agents.voice.turn import TurnHandlingOptions
from livekit.plugins import silero

from ...app.config import get_agent_config, get_config
from ...openclaw.instructions import VOICE_CALL_INSTRUCTION
from ...openclaw.llm import create_llm
from ...providers.stt.whisper import LocalSTT
from ...providers.tts.elevenlabs import get_tts_for_agent

load_dotenv()

logger = logging.getLogger(__name__)

server = agents.AgentServer(
    job_memory_warn_mb=2048,
    job_memory_limit_mb=0,
)


class VoiceAgent(Agent):
    """LiveKit voice agent with voice-first instructions."""

    def __init__(self, instructions: str | None = None, **kwargs: Any) -> None:
        self._voice_instructions = instructions or VOICE_CALL_INSTRUCTION
        super().__init__(instructions=self._voice_instructions, **kwargs)


def _extract_participant_metadata(ctx: agents.JobContext) -> dict[str, Any]:
    """Extract metadata from the first remote participant that provides it."""

    for participant in ctx.room.remote_participants.values():
        if participant.metadata:
            try:
                return json.loads(participant.metadata)
            except (TypeError, json.JSONDecodeError):
                logger.warning("Invalid participant metadata for room %s", ctx.room.name)
    return {}


def _extract_user_info(ctx: agents.JobContext) -> tuple[str, str]:
    """Extract user email and name from participant metadata."""

    metadata = _extract_participant_metadata(ctx)
    return metadata.get("email", ""), metadata.get("name", "")


def _resolve_agent_id(ctx: agents.JobContext, metadata: dict[str, Any]) -> str:
    """Resolve the effective agent id from metadata, room name, and defaults."""

    cfg = get_config()
    requested_agent = str(metadata.get("agent") or "").lower().strip()
    if requested_agent in cfg.agents:
        return requested_agent

    room_name = ctx.room.name or ""
    parts = room_name.split("-")
    if len(parts) >= 3 and parts[0] == "voice" and parts[1] in cfg.agents:
        return parts[1]

    if cfg.voice.default_agent in cfg.agents:
        return cfg.voice.default_agent
    if cfg.agents:
        return next(iter(cfg.agents.keys()))
    raise ValueError("No agents configured in config/agents.yaml")


async def entrypoint(ctx: agents.JobContext):
    """Main voice session entrypoint."""

    metadata = _extract_participant_metadata(ctx)
    user_email, user_name = _extract_user_info(ctx)
    agent_id = _resolve_agent_id(ctx, metadata)
    model_override = metadata.get("model_override") or None
    room_name = ctx.room.name or f"voice-{agent_id}-unknown"
    agent_cfg = get_agent_config(agent_id)
    cfg = get_config()

    logger.info(
        "Starting voice session",
        extra={
            "agent_id": agent_id,
            "session_id": room_name,
            "user_email": user_email or "",
            "user_name": user_name or "",
        },
    )

    session = AgentSession(
        stt=LocalSTT(
            model_size=cfg.voice.stt_model_size,
            language=agent_cfg.language,
            device=cfg.voice.stt_device,
            compute_type=cfg.voice.stt_compute_type,
            beam_size=cfg.voice.stt_beam_size,
        ),
        llm=create_llm(agent_id, model_override),
        tts=get_tts_for_agent(agent_id),
        vad=silero.VAD.load(),
        turn_handling=TurnHandlingOptions(
            interruption={"enabled": True, "mode": "vad"},
        ),
        session_close_transcript_timeout=5.0,
    )

    await session.start(
        room=ctx.room,
        agent=VoiceAgent(instructions=VOICE_CALL_INSTRUCTION),
    )

    logger.info(
        "Voice session started",
        extra={"agent_id": agent_id, "session_id": room_name, "model_override": model_override or ""},
    )


@server.rtc_session()
async def rtc_entrypoint(ctx: agents.JobContext):
    """RTC session entrypoint used by the LiveKit agent server."""

    await entrypoint(ctx)


def _install_signal_handlers() -> dict[signal.Signals, Any]:
    """Install shutdown handlers for graceful worker termination."""

    previous_handlers: dict[signal.Signals, Any] = {}

    def handle_shutdown(signum: int, _frame: Any) -> None:
        signal_name = signal.Signals(signum).name
        logger.info("Shutdown signal received: %s", signal_name)
        raise KeyboardInterrupt

    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            previous_handlers[signum] = signal.getsignal(signum)
            signal.signal(signum, handle_shutdown)
        except ValueError:
            logger.debug("Skipping signal handler install for %s", signum)

    return previous_handlers


def _restore_signal_handlers(previous_handlers: dict[signal.Signals, Any]) -> None:
    """Restore any signal handlers replaced by the worker."""

    for signum, handler in previous_handlers.items():
        signal.signal(signum, handler)


def _cleanup_worker(previous_handlers: dict[signal.Signals, Any]) -> None:
    """Restore process state after worker shutdown."""

    _restore_signal_handlers(previous_handlers)
    logger.info("LiveKit worker cleanup complete")


def main():
    """Run the LiveKit agent server."""

    previous_handlers = _install_signal_handlers()
    try:
        agents.cli.run_app(server)
    except KeyboardInterrupt:
        logger.info("Stopping LiveKit worker")
    finally:
        _cleanup_worker(previous_handlers)
