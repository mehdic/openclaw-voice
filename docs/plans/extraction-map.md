# Phase 1: Extraction Map

## Source implementation
`~/.openclaw/workspace-sevro/projects/livekit-voice/` — 3,059 lines across 35 Python files

---

## Classification

### ✅ Preserve with cleanup (carry to new repo)

| Module | Lines | What it does | Cleanup needed |
|---|---:|---|---|
| `config.py` | 245 | Pydantic config models, YAML+env loading | Remove hardcoded `sevro` defaults. Generalize `default_agent`. Drop `brave_api_key`. Rename `session_cookie_name`. |
| `server/routes.py` | 451 | Flask API: token, auth, agents, models, commands, health | Remove prompt-cache endpoints, session-history endpoints (defer to Phase 4). Strip Google Client ID injection from HTML. Simplify command system. |
| `server/auth.py` | 50 | `login_required` decorator, `is_authenticated` check | Clean — carry as-is. |
| `server/app.py` | 40 | Flask app factory with session config | Clean — carry as-is. |
| `app.py` (entrypoint) | 251 | LiveKit AgentServer, room join, agent/model resolution, session wiring | Remove prompt-cache mode branching. Remove persistence hooks (Phase 4). Remove monkey-patch — replace with explicit config. Remove `_build_resume_context` (Phase 4). |
| `llm/gateway.py` | 40 | OpenClaw gateway LLM via openai plugin | Clean — this IS the core bridge. Carry as-is. |
| `llm/factory.py` | 51 | LLM mode routing (direct vs gateway) | Simplify: MVP is gateway-only. Drop cached/direct branching. Keep as thin factory for future extensibility. |
| `agents/registry.py` | 41 | TTS instance creation per agent | Clean — carry as-is. |
| `agents/voice_instruction.py` | 34 | Default voice system prompt | Review content. Carry and make configurable. |
| `stt/local.py` | 548 | Local faster-whisper STT with Silero VAD streaming | High-value, complex code. Carry with cleanup: extract constants to config, improve error messages. This is the most technically valuable module. |

### 🔄 Rewrite cleanly (same concept, fresh code)

| Module | Lines | Why rewrite |
|---|---:|---|
| `llm/direct.py` | 64 | Only needed for cached mode. Drop from MVP. Rewrite later if cached mode returns. |

### ❌ Drop from MVP

| Module | Lines | Why drop |
|---|---:|---|
| `prompts/cache.py` | 399 | Prompt caching is an optimization, not MVP-critical. Gateway mode handles prompts. Add back in Phase 4 as a performance optimization. |
| `persistence/session_store.py` | 156 | Session persistence is Phase 4 hardening work. |
| `persistence/auto_save.py` | 66 | Depends on persistence — Phase 4. |
| `persistence/transcript_tracker.py` | 181 | Depends on persistence — Phase 4. |
| `persistence/models.py` | 92 | Depends on persistence — Phase 4. |
| `tools/registry.py` | 159 | Direct tool execution. In MVP, all tools go through OpenClaw gateway. Revisit in Phase 4 for latency optimization. |
| `tools/gateway_proxy.py` | 186 | Custom gateway proxy tools (image gen, browser, sessions_send). Not needed when gateway handles tools. |
| `tools/web.py` | ? | Direct web search/fetch. Not MVP. |
| `tools/memory.py` | ? | Direct memory access. Not MVP. |
| `tools/memory_write.py` | ? | Direct memory write. Not MVP. |
| `tools/messaging.py` | ? | Direct message send. Not MVP. |
| `tools/system.py` | ? | Direct session status. Not MVP. |
| `tools/workspace.py` | ? | Workspace browsing. Not MVP. |
| `tools/files.py` | ? | File search. Not MVP. |
| `tools/exec_tool.py` | ? | Command execution. Not MVP. |
| `web/index.html` | ~800 | Monolithic single-file UI. Rewrite as cleaner multi-file thin frontend. |

---

## MVP behavior contract

The following behaviors MUST be preserved in the new implementation. These are the acceptance criteria.

### 1. Authentication gate
- Google OAuth via `/api/auth/google`
- Server-side session with secure cookies
- `login_required` decorator on all sensitive endpoints
- Email allowlist enforcement
- Demo mode as explicit opt-in config option
- `/api/session` returns auth state + allowed agents

### 2. Agent resolution
- Agent determined by: participant metadata > room name parsing > default config
- Room name convention: `voice-{agentId}-{timestamp}`
- Participant metadata carries: `agent`, `email`, `name`, `model_override`
- Per-user agent allowlist from config

### 3. Model override
- Users can switch models via `/api/command` (`/model <name>`)
- Model allowlist per agent from config
- Override stored in session, passed through participant metadata
- Override applied via `x-openclaw-model` header on gateway calls

### 4. Token issuance
- `/api/token` mints LiveKit AccessToken
- Token includes room name, identity (sanitized email), and metadata
- Metadata embeds agent, email, name, model_override
- Requires authentication

### 5. OpenClaw gateway bridge
- LLM calls route to `{openclaw_url}/v1/chat/completions`
- Model field: `openclaw/{agent_id}`
- Header: `x-openclaw-model: {effective_model}`
- Auth: `api_key` from config
- Timeout: configurable (default 90s read)

### 6. Voice pipeline
- STT: local faster-whisper with configurable model size, language, device
- VAD: Silero with configurable thresholds
- TTS: ElevenLabs with per-agent voice config
- Turn handling: VAD-based interruption enabled
- Streaming: interim + final transcripts

### 7. Frontend capabilities (minimum)
- Connect / disconnect
- Mute toggle
- Agent picker (from allowed list)
- Connection status indicator
- Signed-in user display

### 8. Health and status
- `/health` endpoint (no auth)
- Structured logging with agent_id, session_id, timing

---

## Existing hacks to NOT carry forward

### 1. INTERRUPTION_TIMEOUT monkey-patch
**Current:** `import livekit.agents.voice.speech_handle as _sh; _sh.INTERRUPTION_TIMEOUT = 30.0`
**Problem:** Fragile, breaks on SDK updates, not discoverable
**New approach:** Use `TurnHandlingOptions` config. If SDK doesn't expose this, document the limitation and pin the SDK version. File upstream issue if needed.

### 2. Hardcoded personal defaults
**Current:** `default_agent: "sevro"`, personal email addresses, macOS keychain access for Google API key
**New approach:** All defaults must be generic. No personal identity in committed code.

### 3. Asyncio event loop gymnastics in Flask routes
**Current:** `server/routes.py` has try/except around `get_event_loop()` + `ThreadPoolExecutor` fallback
**Problem:** Fragile, race-prone
**New approach:** Use `asyncio.run()` consistently in sync Flask handlers, or switch to an async framework.

### 4. `src` import path issues
**Current:** `agents/registry.py` uses `from src.voice_agent.config import ...` (absolute from src root)
**New approach:** Consistent relative imports within the package.

### 5. Prompt cache tight coupling
**Current:** `app.py` entrypoint has complex branching for cached vs gateway mode
**New approach:** MVP is gateway-only. No prompt cache branching in core flow.

---

## File-to-file mapping (old → new)

| Old path | New path | Action |
|---|---|---|
| `config.py` | `src/openclaw_voice/app/config.py` | Cleanup + generalize |
| `server/app.py` | `src/openclaw_voice/app/server.py` | Carry as-is |
| `server/auth.py` | `src/openclaw_voice/app/auth.py` | Carry as-is |
| `server/routes.py` | `src/openclaw_voice/app/routes.py` | Simplify (drop cache/persistence endpoints) |
| `app.py` | `src/openclaw_voice/runtime/livekit/worker.py` | Simplify (gateway-only, no persistence) |
| `llm/gateway.py` | `src/openclaw_voice/openclaw/client.py` | Carry as-is |
| `llm/factory.py` | `src/openclaw_voice/openclaw/llm.py` | Simplify (gateway-only) |
| `agents/registry.py` | `src/openclaw_voice/providers/tts/elevenlabs.py` | Carry as-is |
| `agents/voice_instruction.py` | `src/openclaw_voice/openclaw/instructions.py` | Make configurable |
| `stt/local.py` | `src/openclaw_voice/providers/stt/whisper.py` | Cleanup constants |
| `web/index.html` | `src/openclaw_voice/web/static/` | Rewrite (Phase 3) |

---

## Extraction order (recommended)

1. **Config** — everything else depends on it
2. **OpenClaw client** (gateway.py) — the core bridge
3. **Auth** — gates everything
4. **Token endpoint** (from routes.py) — connects auth to LiveKit
5. **LiveKit worker** (from app.py) — the voice runtime
6. **STT** (local.py) — the most complex provider
7. **TTS** (registry.py) — straightforward
8. **Routes** (remaining endpoints) — agent list, models, commands
9. **Frontend** — last, because it depends on all API endpoints
