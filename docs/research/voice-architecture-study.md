# OpenClaw Voice, architecture study

## Purpose

This document evaluates the best way to create a simple, open source, quick-install voice layer for OpenClaw, based on:

- the existing local LiveKit implementation
- Pipecat and LiveKit public docs and repo documentation
- OpenClaw's current extension and plugin patterns
- industry-standard voice agent architecture choices in 2026
- community examples where external products were bridged into OpenClaw

The goal is not to pick the most fashionable framework. The goal is to ship the fastest, clearest, lowest-friction OSS project that gives OpenClaw users a real voice option without making them fight infrastructure.

## Executive summary

### Recommendation

Build **v1 on top of the current LiveKit-based implementation**, then refactor it into a cleaner OSS-friendly project shape with a backend abstraction boundary so a Pipecat backend can be added later.

### Why

1. The current implementation already solved the expensive problems: auth, agent selection, session mapping, OpenClaw gateway calls, WebRTC join flow, public ingress, and real-world latency issues.
2. Pipecat is attractive for voice-pipeline ergonomics, but it does not erase the productization work. It mostly moves that work into a different architecture.
3. A quick-install OSS project wins on adoption only if it is easy to understand, easy to run, and easy to debug. Starting from battle-tested code gets there faster.
4. OpenClaw itself is evolving voice capabilities, including official voice-call and realtime provider plumbing. A clean LiveKit-first bridge can ship now without blocking future native OpenClaw voice work.

### Short version

- **Best path to MVP:** productize current LiveKit work.
- **Best path to long-term flexibility:** introduce a transport/backend boundary after MVP.
- **Best path for future experimentation:** add Pipecat as an optional backend in v2 or v3.

## Evidence reviewed

### Local implementation

- `/Users/mehdichaouachi/.openclaw/workspace-sevro/projects/livekit-voice/README.md`
- `/Users/mehdichaouachi/.openclaw/workspace-sevro/projects/livekit-voice/pyproject.toml`
- `/Users/mehdichaouachi/.openclaw/workspace-sevro/projects/livekit-voice/start.sh`
- `/Users/mehdichaouachi/.openclaw/workspace-sevro/projects/livekit-voice/src/voice_agent/app.py`
- `/Users/mehdichaouachi/.openclaw/workspace-sevro/projects/livekit-voice/src/voice_agent/config.py`
- `/Users/mehdichaouachi/.openclaw/workspace-sevro/projects/livekit-voice/src/voice_agent/server/routes.py`
- `/Users/mehdichaouachi/.openclaw/workspace-sevro/projects/livekit-voice/src/voice_agent/server/auth.py`
- `/Users/mehdichaouachi/.openclaw/workspace-sevro/projects/livekit-voice/web/index.html`
- `/Users/mehdichaouachi/.openclaw/workspace/memory/infra/livekit-voice.md`
- project audit files: `REVIEW.md`, `FINAL_AUDIT.md`, `TEST_RESULTS.md`, `REFACTOR_PLAN.md`

### OpenClaw internals and docs

- `/opt/homebrew/lib/node_modules/openclaw/dist/extensions/voice-call/openclaw.plugin.json`
- `/opt/homebrew/lib/node_modules/openclaw/dist/extensions/talk-voice/openclaw.plugin.json`
- `https://docs.openclaw.ai/automation/hooks`
- OpenClaw distribution metadata showing realtime voice and transcription provider registries, webhooks, and plugin-sdk boundaries
- public issue: `https://github.com/openclaw/openclaw/issues/8088`

### Public ecosystem references

- Pipecat repo overview: `https://github.com/pipecat-ai/pipecat`
- Pipecat quickstart: `https://docs.pipecat.ai/getting-started/quickstart`
- Pipecat Voice UI Kit: `https://github.com/pipecat-ai/voice-ui-kit`
- LiveKit Agents repo overview: `https://github.com/livekit/agents`
- LiveKit voice AI quickstart: `https://docs.livekit.io/agents/start/voice-ai/`
- third-party tutorial: `https://www.clawctl.com/blog/build-voice-chat-openclaw-15-minutes`
- community OpenClaw skill example: `https://github.com/box-community/openclaw-box-skill`
- community OpenClaw voice/STT example discussed in Pipecat issue: `https://github.com/pipecat-ai/pipecat/issues/4016`

## What exists today, locally

The current implementation is not a toy. It is a real end-to-end voice product slice.

### Current shape

The local stack is roughly:

- browser UI + token server on Flask
- Google auth gate
- LiveKit room/token flow
- LiveKit agent worker in Python
- local faster-whisper STT with Silero VAD
- OpenClaw gateway as the LLM and tool brain
- ElevenLabs TTS
- public ingress through AWS nginx and forwarded TURN/WebRTC ports

### Strengths already earned

#### 1. The OpenClaw bridge is real and useful

The current code does not build a fake side bot. It uses OpenClaw as the real assistant backend. In `src/voice_agent/app.py`, the room metadata and room naming conventions determine the target agent and optional model override before creating the LLM instance. In `src/voice_agent/server/routes.py`, `/api/token` mints a LiveKit token and embeds OpenClaw agent metadata into participant metadata.

That means the system already solved the most important product question: how voice sessions map to OpenClaw agents and user sessions.

#### 2. Config is centralized and validated

`src/voice_agent/config.py` shows a strong move toward OSS-readiness:

- typed config models
- YAML plus env loading
- agent-level settings
- default user and per-user access
- central timeouts

That is exactly the kind of structure worth preserving.

#### 3. Real operational scars were already paid for

The infra memory doc records issues most greenfield voice projects only discover later:

- LiveKit `--dev` versus real config keys
- VAD interruption mode pitfalls
- hardcoded `INTERRUPTION_TIMEOUT` causing mid-tool-call silence
- macOS process model confusion
- TURN and port-forwarding realities
- STT latency and hallucination tuning
- TTS latency tradeoffs

This is battle-tested knowledge. Throwing it away to start over on Pipecat would be expensive.

#### 4. The UI product shape is already credible

The current `web/index.html` is not just a transport test page. It includes:

- sign-in state
- allowed agent selection
- model switching
- call control
- session continuity affordances

That is already more productized than most voice demos.

### What should not be carried forward unchanged

#### 1. Infra assumptions tied to one personal deployment

The current stack depends on specific host topology:

- Mac Mini runtime
- AWS nginx relay
- manual TURN/media forwarding
- launchd watchdog
- custom DNS and certificate shape

That is acceptable for a private deployment, but too opinionated for a quick-install OSS project.

#### 2. Monkey patches and local survival hacks

The `INTERRUPTION_TIMEOUT = 30.0` patch in `src/voice_agent/app.py` is a good operational fix, but it is a sign that the OSS project needs an explicit interruption policy layer and version-pinned SDK behavior, not hidden patches as the first story.

#### 3. Monolithic project concerns

The current code mixes:

- frontend delivery
- auth
- transport sessioning
- agent orchestration
- deployment behavior
- prompt caching

The next project should separate product concerns more deliberately.

#### 4. Deployment complexity is still too high for general adoption

The current implementation can work well, but it is not yet "clone, set env, run" simple. The OSS project must reduce setup friction hard.

## Public landscape, what people have already done

### Confirmed public Pipecat + OpenClaw example

The clearest public example found is the Clawctl article, "How to Build a Voice Chat Interface for OpenClaw". It describes:

- Deepgram STT
- ElevenLabs TTS
- Pipecat orchestration
- OpenClaw Gateway via OpenAI-compatible `/v1/chat/completions`
- thin browser client

This is important evidence for two reasons:

1. It confirms that a Pipecat bridge to OpenClaw is technically straightforward.
2. It also shows the main pattern used by outsiders: treat OpenClaw as the brain behind a standard API, and let another voice framework own the live conversation loop.

### What was not found

There is **not** strong evidence yet of a large ecosystem of independent OSS projects doing Pipecat + OpenClaw integration at scale.

So the honest conclusion is:

- the pattern exists
- it is credible
- it is not yet a crowded, proven category

### Related OpenClaw voice direction

OpenClaw issue `#8088`, "Real-time voice call support (bidirectional audio)", explicitly lists the main options the core project itself sees:

- LiveKit Agents integration
- Pipecat bridge
- OpenAI Realtime API support
- WebRTC endpoint in the gateway

That means the paths considered in this study are aligned with OpenClaw's own strategic direction.

## Industry standards for voice-agent projects in 2026

Across Pipecat, LiveKit, and adjacent voice-agent stacks, the common architecture patterns are now pretty consistent.

### 1. Separate transport from intelligence

Industry-standard stacks treat these as separate layers:

- **transport/media:** WebRTC, telephony, rooms, streams
- **conversation pipeline:** STT, VAD, turn-taking, LLM, TTS
- **agent brain/application state:** session, tools, memory, auth, business logic
- **frontend:** browser or native client

This is the biggest design principle to adopt.

### 2. WebRTC is the default for browser voice

For interactive browser voice, WebRTC is the standard because it provides:

- low latency audio transport
- ICE/TURN/NAT traversal
- duplex streaming
- mature browser support

Anything that avoids WebRTC usually pays for it later in latency or device compatibility.

### 3. Barge-in and turn detection are first-class UX requirements

Modern voice systems treat the following as core UX, not polish:

- interruptibility
- partial transcript handling
- VAD tuning
- short response style
- recovery from silence or tool latency

### 4. Thin frontend, opinionated backend

The winning pattern is usually:

- thin frontend for connect, disconnect, status, mute, session, avatar
- most logic on the backend

This keeps browser complexity low and makes multi-client reuse easier.

### 5. Strong observability

Good voice projects now treat these as mandatory:

- per-turn latency tracing
- STT/TTS timing breakdown
- conversation event logs
- transport state visibility
- error classification by stage

### 6. Provider optionality is valuable, but too much abstraction too early is poison

It is useful to support multiple STT/TTS/LLM providers, but many projects fail by abstracting too early. MVPs should support one or two good paths well, then generalize.

### 7. Auth and session identity cannot be bolted on later

Especially for OpenClaw, the key problem is not just "audio in, audio out." The key problem is:

- which user is this
- which agent is this
- which session is this
- which tools and models are allowed

The local LiveKit implementation already treats this seriously. That should continue.

## How OpenClaw usually integrates external systems

OpenClaw already shows several integration patterns.

### Pattern 1, plugin and provider registration

OpenClaw's plugin system supports provider registration for things like realtime voice, transcription, channels, and webhooks. The official `voice-call` extension config schema shows a classic OpenClaw pattern:

- strong config schema
- runtime provider resolution
- optional provider-specific sub-config
- clear UI hints for setup
- security controls around webhooks and public exposure

Implication: a new voice project should not fight OpenClaw's extension model. It should align with it.

### Pattern 2, external bridge over stable APIs

The Clawctl Pipecat tutorial uses OpenClaw's OpenAI-compatible chat endpoint instead of embedding itself deeply into OpenClaw internals.

Implication: external voice projects can move fast by consuming stable gateway APIs instead of patching core runtime behavior.

### Pattern 3, skill wrapper around external tools

Projects like the Box skill integrate external products by wrapping an external CLI or API inside OpenClaw skill conventions:

- skill-local docs and metadata
- user-supplied credentials
- explicit non-goals around secret provisioning
- developer-preview posture when support burden is high

Implication: the new voice project should be explicit about what it does and does not own. It should not pretend to solve all OpenClaw voice problems in v1.

### Pattern 4, self-hosted provider bridge

OpenClaw's broader provider ecosystem repeatedly uses "OpenAI-compatible bridge" and "self-hosted provider" patterns.

Implication: if the project needs to stay loosely coupled, an API boundary is healthy.

## Option analysis

## Option A, productize the current LiveKit-based implementation

### Description

Take the local LiveKit voice app, strip out personal deployment assumptions, simplify setup, and publish it as a standalone OSS repo focused on quick install.

### Advantages

- fastest path to something useful
- built on proven session and auth behavior
- already close to product shape
- strongest reuse of existing scars and fixes
- LiveKit has excellent transport, room, and client maturity
- easy future path to telephony or native clients

### Disadvantages

- transport stack is heavier than a tiny Pipecat demo
- TURN and WebRTC setup can still intimidate users if not packaged well
- LiveKit concepts may feel big for users who just want local browser voice
- current architecture still carries some historical refactor baggage

### Complexity

- **MVP:** medium
- **long-term:** medium

### Time to MVP

Best among all realistic options.

### OSS adoption risk

Moderate, but manageable if setup is simplified with strong defaults.

### Verdict

Best v1 option.

## Option B, rebuild around Pipecat

### Description

Start a new project that uses Pipecat as the primary voice pipeline engine, then point its LLM layer at OpenClaw.

### Advantages

- cleaner voice-native pipeline model
- easier experimentation with STT/TTS/VAD stacks
- lighter conceptual model for the voice brain itself
- official client SDKs and Voice UI Kit reduce some frontend work
- strong fit for benchmarking and future multimodal extensions

### Disadvantages

- redoes already-solved integration work
- still requires custom OpenClaw auth/session/agent mapping
- still needs a frontend decision and packaging strategy
- more architecture uncertainty for first release
- lower confidence because local production scars were earned on LiveKit, not Pipecat

### Complexity

- **MVP:** medium to high
- **long-term:** medium

### Time to MVP

Slower than Option A.

### OSS adoption risk

Higher for v1 because setup is less anchored in what is already known to work end-to-end with OpenClaw.

### Verdict

Very good experimental path, not the best first shipping path.

## Option C, hybrid architecture with pluggable backend

### Description

Define a stable app shell, session/auth layer, and frontend contract, but let the voice runtime backend be swappable:

- `livekit`
- `pipecat`
- maybe later `openclaw-native`

### Advantages

- best long-term design
- avoids locking the project to one voice engine
- allows comparative testing and migration
- lets v1 launch on LiveKit without closing the door to Pipecat

### Disadvantages

- dangerous if attempted too early
- abstraction can become ceremony before real needs are proven
- backend parity can slow feature delivery

### Complexity

- **MVP if done narrowly:** medium
- **MVP if overbuilt:** high

### Time to MVP

Good only if backend abstraction is kept very thin.

### Verdict

Best structural direction, but only after selecting one concrete implementation path for v1.

## Option D, direct OpenClaw-native web voice path

### Description

Do not build a standalone bridge product. Instead, invest directly in OpenClaw-native browser voice using core runtime capabilities, plugin registries, and future official UI work.

### Advantages

- best eventual user experience if core OpenClaw adopts it
- fewer moving parts in the long term
- cleaner agent/session semantics inside the platform

### Disadvantages

- not the fastest path to a separate OSS project
- depends on core OpenClaw roadmap and coordination
- reduces freedom to ship fast and opinionated

### Complexity

- **MVP in core:** high
- **long-term platform win:** very high upside

### Verdict

Good strategic future path, not the right first move for this new standalone project.

## Comparative scorecard

| Path | Time to MVP | Uses existing battle scars | Setup simplicity potential | Architecture elegance | Future flexibility | Recommendation |
|---|---:|---:|---:|---:|---:|---|
| A. Productize current LiveKit app | 9/10 | 10/10 | 7/10 | 7/10 | 8/10 | **Start here** |
| B. New Pipecat-first rebuild | 5/10 | 4/10 | 7/10 | 8/10 | 8/10 | Good v2 candidate |
| C. Hybrid pluggable runtime | 7/10 | 8/10 | 8/10 | 9/10 | 10/10 | Do after MVP, not before |
| D. Direct OpenClaw-native voice | 3/10 | 5/10 | 10/10 if core lands | 10/10 | 9/10 | Long-term platform direction |

## Recommended product shape

## Product thesis

The new project should be:

- a **simple OpenClaw voice launcher**
- not a general voice-agent framework
- not a replacement for OpenClaw core voice work
- not a giant infrastructure product

### Proposed positioning

**OpenClaw Voice**

A lightweight, self-hostable voice companion for OpenClaw that gives users a browser-based talk mode with minimal setup.

### Core promise

- quick install
- browser voice UI
- real OpenClaw agent sessions
- safe defaults
- simple deployment story
- swappable voice backend later

## What to preserve from the current implementation

- room/session naming convention carrying agent identity
- user auth gate before token issuance
- per-user allowed agent filtering
- model override support tied to agent policy
- centralized config model
- operational knowledge around VAD, STT, TTS, and interruption behavior
- strong separation between voice frontend/token API and OpenClaw gateway brain
- local STT option for privacy-sensitive users

## What to replace or redesign

- personal deployment assumptions and hardcoded domains
- launchd and AWS-specific docs as the default story
- hidden monkey-patch behavior without explicit config and version notes
- sprawling single-page UI file as the long-term frontend pattern
- coupling between prompt-cache internals and the voice product unless it clearly improves UX

## Target v1 architecture

### Backend modules

1. **web app server**
   - serve frontend
   - auth/session cookies
   - health
   - issue voice session tokens or offers

2. **OpenClaw bridge**
   - resolve agent
   - resolve session id
   - resolve model override policy
   - call OpenClaw gateway

3. **voice runtime adapter**
   - initially LiveKit
   - later optional Pipecat

4. **provider modules**
   - STT
   - TTS
   - optional local inference pieces

5. **observability**
   - per-turn logs
   - latency timing
   - failure stage classification

### Frontend

Keep it intentionally thin:

- connect/disconnect
- mute
- agent picker
- status
- minimal transcript view
- optional settings drawer

Do not build a full chat replacement in v1.

### Suggested boundary design

Define a small internal contract like:

- `createVoiceSession(user, agent, modelOverride)`
- `connectTransport(session)`
- `emitUserSpeech(partial/final)`
- `emitAssistantSpeech(text/audio)`
- `recordMetrics(turn)`

If that contract is clean, LiveKit can power it first and Pipecat can be added later.

## Deployment recommendation

For the OSS project, support two official deployment stories at launch:

### Story 1, local dev and personal LAN/Tailscale

This should be the default getting-started mode.

- run OpenClaw locally
- run voice app locally
- access from same machine or Tailscale
- avoid forcing public TURN complexity on day one

### Story 2, reverse-proxied public deployment

Support this as a documented advanced path, not the default first experience.

If LiveKit remains the backend, provide one opinionated reference deployment, not six.

## Security and trust model

This project sits in a sensitive place because it turns speech into tool-capable agent actions.

Minimum standards:

- require auth by default for non-demo mode
- explicit user-to-agent authorization mapping
- session cookies and CSRF posture documented
- rate limiting and basic abuse controls on token/offer endpoints
- clear distinction between demo mode and authenticated mode
- do not expose an unauthenticated public voice endpoint by accident

## Key product decisions

### Decision 1, standalone repo first

Do not begin inside OpenClaw core. Build a standalone OSS repo first.

### Decision 2, LiveKit for v1 runtime

Use LiveKit first because it matches the battle-tested implementation and offers production-grade browser transport.

### Decision 3, backend abstraction only where immediately useful

Create a thin runtime adapter boundary, not a giant framework.

### Decision 4, OpenClaw remains the brain

Do not duplicate agent memory, tools, or business logic outside OpenClaw.

### Decision 5, low-ceremony frontend

The first frontend should be intentionally simple and portable.

## What Pipecat should still be used for

Pipecat should remain a strategic benchmark and possibly a future backend for:

- lower-ceremony experimentation
- alternate STT/TTS pipelines
- structured dialog flows
- multimodal extensions
- evaluating whether LiveKit transport is overkill for some users

In other words, Pipecat is not rejected. It is deferred until the product shape is stable.

## Risks and mitigations

| Risk | Why it matters | Mitigation |
|---|---|---|
| Over-engineering abstraction too early | Slows shipping | Start with one backend, one happy path |
| WebRTC/TURN setup scares users | Adoption killer | make local/Tailscale mode the default |
| Voice UX regressions from tool latency | Feels broken fast | explicit interruption policy and turn timers |
| OpenClaw auth/session mismatches | Wrong agent or wrong permissions is unacceptable | keep auth and token issuance in one server boundary |
| Backend lock-in | hard to compare Pipecat later | define minimal runtime contract now |
| Core OpenClaw voice catches up fast | project could become redundant | position project as quickstart and experimentation layer |

## Final recommendation

Ship a new OSS project that is:

- **inspired by the current local LiveKit implementation**
- **cleaned up for public reuse**
- **scoped for quick install and browser voice**
- **architected with a narrow runtime adapter boundary**
- **designed so Pipecat can be added later if it proves materially better**

That is the highest-probability path to a real, adoptable project.

If the mission is to help OpenClaw users get voice quickly, then the winning move is not to restart the war from scratch. It is to turn the scars already earned into a clean, sharp, reusable weapon.