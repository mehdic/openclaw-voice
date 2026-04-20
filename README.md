<div align="center">

# 🎙️ OpenClaw Voice

**Talk to your OpenClaw agents from a browser.**

A lightweight, self-hostable voice companion for [OpenClaw](https://github.com/openclaw/openclaw) that turns any agent into a real-time voice conversation — with minimal setup.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

</div>

---

## What it does

OpenClaw Voice gives your OpenClaw agents a voice. You open a browser, pick an agent, and start talking. Your speech is transcribed, sent to OpenClaw, and the response is spoken back to you — all in real time.

**OpenClaw stays the brain.** This project only handles the voice layer: audio transport, speech-to-text, text-to-speech, and a thin browser UI. All intelligence, tools, memory, and agent behavior remain in OpenClaw where they belong.

## How it works

```
Browser (WebRTC) → LiveKit → Voice Agent Worker
                                  ├── STT (faster-whisper, local)
                                  ├── LLM (OpenClaw gateway)
                                  └── TTS (ElevenLabs)
```

1. You speak into the browser
2. Audio streams over WebRTC to a LiveKit room
3. An agent worker transcribes your speech locally
4. The transcript hits your OpenClaw gateway as a standard chat completion
5. OpenClaw responds with the full power of your configured agent
6. The response is converted to speech and streamed back

## Features

- 🗣️ **Real-time voice** — low-latency WebRTC audio, full duplex
- 🧠 **OpenClaw-native** — uses your existing agents, tools, memory, and models
- 🎯 **Agent picker** — choose which OpenClaw agent to talk to
- 🔒 **Auth built in** — Google OAuth or explicit demo mode
- 🏠 **Self-hostable** — runs on your hardware, your network, your rules
- ⚡ **Local STT** — faster-whisper runs on-device, no cloud transcription needed
- 🎭 **Per-agent voices** — configure different TTS voices per agent
- 📊 **Observable** — structured logs with per-turn latency breakdown

## Quick start

### Prerequisites

- Python 3.11+
- A running [OpenClaw](https://github.com/openclaw/openclaw) instance
- A running [LiveKit](https://docs.livekit.io/home/self-hosting/local/) server
- An [ElevenLabs](https://elevenlabs.io) API key (for TTS)

### Install

```bash
git clone https://github.com/mehdic/openclaw-voice.git
cd openclaw-voice

# Create your config
cp env.example .env
# Edit .env with your OpenClaw URL, LiveKit keys, and ElevenLabs key

# Install
pip install -e .

# Run
python -m openclaw_voice
```

Open `http://localhost:7890` in your browser. Pick an agent. Start talking.

### With uv (recommended)

```bash
git clone https://github.com/mehdic/openclaw-voice.git
cd openclaw-voice
cp env.example .env
# Edit .env

uv sync
uv run python -m openclaw_voice
```

## Configuration

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `OPENCLAW_URL` | ✅ | Your OpenClaw gateway URL |
| `OPENCLAW_TOKEN` | ✅ | Gateway auth token |
| `LIVEKIT_URL` | ✅ | LiveKit server WebSocket URL |
| `LIVEKIT_API_KEY` | ✅ | LiveKit API key |
| `LIVEKIT_API_SECRET` | ✅ | LiveKit API secret |
| `ELEVEN_API_KEY` | ✅ | ElevenLabs API key |
| `AUTH_MODE` | | `google` or `demo` (default: `demo`) |
| `WEB_PORT` | | Server port (default: `7890`) |

### Agent config

Edit `config/agents.yaml` to define which OpenClaw agents are available and how they sound:

```yaml
agents:
  reaper:
    display_name: "Reaper"
    emoji: "⚔️"
    voice:
      provider: elevenlabs
      voice_id: pNInz6obpgDQGcFmaJgB
    llm:
      model: anthropic/claude-sonnet-4-5
```

## Architecture

```
src/openclaw_voice/
├── app/            # Web server, auth, health
├── openclaw/       # Gateway client, agent resolution, session mapping
├── runtime/        # Voice backend adapters
│   └── livekit/    # LiveKit implementation (default)
├── providers/      # STT and TTS provider modules
│   ├── stt/
│   └── tts/
└── web/            # Browser frontend
    └── static/
```

The architecture uses a **runtime adapter** pattern. LiveKit is the default (and currently only) backend. The boundary is designed so alternative backends (like [Pipecat](https://github.com/pipecat-ai/pipecat)) can be added later without rewriting the product shell.

## Project status

🚧 **Early development** — the architecture study and phased plan are complete. MVP implementation is next.

See the [phased implementation plan](docs/plans/phased-implementation-plan.md) and [architecture study](docs/research/voice-architecture-study.md) for full context.

## Roadmap

| Phase | Status | Description |
|---|---|---|
| 0. Foundation | ✅ | Repo, docs, ADRs |
| 1. Extract core | 🔜 | Port battle-tested implementation |
| 2. Architecture | 🔜 | Clean internal design |
| 3. MVP | 🔜 | Working voice-to-OpenClaw |
| 4. Harden | ⏳ | Tests, lifecycle, deployment docs |
| 5. Runtime seam | ⏳ | Pluggable backend interface |
| 6. Pipecat | ⏳ | Optional alternative backend |

## Contributing

Contributions welcome. See the [issue backlog](https://github.com/mehdic/openclaw-voice/issues) for where to start.

## License

[MIT](LICENSE)

---

<div align="center">

*Per aspera ad astra.*

</div>
