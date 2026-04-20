# OpenClaw Voice, phased implementation plan

## Planning principles

This plan is designed to be executed sequentially. Each phase has:

- a purpose
- concrete tasks
- deliverables
- exit criteria
- explicit non-goals

The plan assumes the product recommendation from the study:

- **v1 backend:** LiveKit-based
- **product shape:** standalone OSS repo
- **architecture rule:** preserve a narrow seam for a future Pipecat backend

## Phase 0, framing and repo foundation

### Goal

Turn the current empty repo into a public-ready project skeleton with a clear scope and decision record.

### Tasks

1. Finalize project name.
   - Chosen name: `openclaw-voice`
2. Add core repo docs.
   - `README.md`
   - `LICENSE`
   - `CONTRIBUTING.md`
   - `SECURITY.md`
   - `docs/architecture.md`
3. Write a tight project charter.
   - what the project is
   - who it is for
   - what it does not try to solve
4. Capture architecture decisions as ADRs.
   - ADR-001: standalone repo first
   - ADR-002: LiveKit backend for MVP
   - ADR-003: thin runtime adapter seam for future Pipecat
   - ADR-004: OpenClaw stays the agent brain
5. Decide the initial runtime language split.
   - likely Python backend plus static or lightweight JS frontend
6. Decide the packaging story.
   - local dev
   - Docker compose optional or later
   - Tailscale/LAN-friendly first-run path

### Deliverables

- public-facing repo skeleton
- architecture decision records
- stable naming and scope

### Exit criteria

- a new contributor can read the README and understand the mission in under 5 minutes
- the MVP scope is unambiguous

### Non-goals

- writing production code
- final deployment automation

## Phase 1, extract and simplify the battle-tested core

### Goal

Identify exactly which parts of the local LiveKit implementation should be carried over into the new repo, and reduce them to the minimum viable core.

### Tasks

1. Inventory the current implementation.
   - auth
   - token issuance
   - room naming
   - agent resolution
   - model override handling
   - STT
   - TTS
   - frontend UI
   - prompt caching hooks
   - deployment scripts
2. Classify each part as one of:
   - preserve mostly as-is
   - preserve with cleanup
   - rewrite cleanly
   - drop from MVP
3. Extract the MVP-critical flows.
   - login or trusted demo gate
   - select agent
   - get transport token/offer
   - connect voice session
   - bridge speech to OpenClaw
4. Write contract tests around the extracted behavior before major rewrites.
5. Remove deployment-specific assumptions.
   - hardcoded domains
   - personal account assumptions
   - launchd/AWS-specific defaults
6. Explicitly document existing hacks.
   - interruption timeout patch
   - worker lifecycle workarounds
   - transport gotchas

### Deliverables

- extraction map from old implementation to new repo
- MVP behavior contract document
- test checklist for preserved behavior

### Exit criteria

- every important part of the current implementation is categorized
- there is agreement on what is in or out for MVP

### Non-goals

- supporting multiple backends yet
- polishing UX beyond the basic flow

## Phase 2, design the new internal architecture

### Goal

Create a clean structure that supports LiveKit now and Pipecat later without premature framework-building.

### Recommended module layout

```text
src/
  app/
    server
    auth
    config
    observability
  openclaw/
    client
    session_mapper
    policy
  runtime/
    base.py
    livekit/
    # pipecat/ later
  providers/
    stt/
    tts/
  web/
    static/
    ui/
```

### Tasks

1. Define config model.
   - OpenClaw gateway URL/token
   - auth mode
   - runtime backend
   - STT/TTS provider config
   - frontend defaults
2. Define runtime adapter interface.
   - create session
   - join or connect
   - publish user audio events
   - receive assistant output
   - expose lifecycle hooks and metrics
3. Define OpenClaw bridge interface.
   - agent resolution
   - session id strategy
   - model policy
   - request shaping for OpenClaw gateway
4. Define auth modes.
   - authenticated mode
   - demo/dev mode with explicit warning
5. Define observability model.
   - turn id
   - connection id
   - session id
   - stage latencies
   - provider timings
6. Define frontend-to-backend API.
   - session info
   - list agents
   - connect token or offer
   - disconnect
   - mute state
   - transcript stream or events

### Deliverables

- architecture diagram
- internal interfaces documented
- API contract for frontend and runtime

### Exit criteria

- implementation can start without architectural ambiguity
- Pipecat future support is possible without contaminating MVP scope

### Non-goals

- building the Pipecat backend now
- building telephony support now

## Phase 3, MVP implementation

### Goal

Ship a usable first version that a technically comfortable OpenClaw user can install and run.

## MVP scope

### Must have

- browser voice UI
- one backend, LiveKit
- authenticated agent selection
- OpenClaw-backed responses
- one good STT path
- one good TTS path
- simple local install
- basic transcript and connection status
- basic health checks and logs

### Nice to have

- model override picker
- persistent last-used agent
- local STT option plus hosted STT option

### Not in MVP

- Pipecat backend
- telephony
- native mobile apps
- full OpenClaw chat UI replacement
- advanced analytics dashboard

### Tasks

1. Implement config loading and validation.
2. Implement OpenClaw client layer.
3. Implement agent/session mapping.
4. Implement LiveKit runtime adapter.
5. Implement token or session endpoint.
6. Implement basic auth.
   - preferably pluggable
   - start with simple documented option
7. Build the thin frontend.
   - connect
   - disconnect
   - mute
   - agent picker
   - connection status
   - lightweight transcript or activity indicators
8. Implement structured logs and health endpoint.
9. Add first-run setup guide.
10. Add env example and minimal bootstrap command.

### Deliverables

- running MVP
- install guide
- sample env file
- screenshots or demo recording

### Exit criteria

- a new user can run the project locally against an existing OpenClaw instance
- the user can talk to a selected OpenClaw agent from a browser
- the install path takes less than 30 minutes for a technical user

## Phase 4, harden the MVP

### Goal

Turn the MVP from a demo into a stable open source release candidate.

### Tasks

1. Add tests.
   - config tests
   - auth tests
   - session mapping tests
   - API endpoint tests
   - smoke tests for voice flow where feasible
2. Improve lifecycle handling.
   - graceful startup and shutdown
   - worker restarts
   - stale session cleanup
3. Add observability.
   - per-turn timing
   - provider timing
   - connection failure reasons
4. Add explicit interruption policy config.
5. Add error UX.
   - mic permissions
   - token failure
   - backend unavailable
   - OpenClaw auth issues
6. Add deployment references.
   - local only
   - Tailscale
   - reverse-proxy public deployment
7. Document security posture.
   - auth defaults
   - public exposure warnings
   - secrets handling

### Deliverables

- v0.1 release candidate
- troubleshooting guide
- deployment guide
- known limitations list

### Exit criteria

- common failure modes are documented and recoverable
- first external testers can install it without hand-holding

## Phase 5, introduce the runtime seam properly

### Goal

Make the architecture truly backend-pluggable after the LiveKit MVP is working.

### Tasks

1. Refactor any LiveKit-specific assumptions leaking upward.
2. Finalize the runtime adapter contract.
3. Ensure frontend is backend-agnostic where possible.
4. Move provider-independent logic into shared modules.
5. Add conformance tests for runtime implementations.

### Deliverables

- stable runtime interface
- backend conformance test suite
- reduced coupling between product shell and LiveKit

### Exit criteria

- a second runtime could be added without large app surgery

### Non-goals

- full parity across multiple runtimes immediately

## Phase 6, Pipecat exploration track

### Goal

Evaluate Pipecat as an optional backend after the product shape is proven.

### Tasks

1. Build a thin Pipecat adapter spike.
2. Reuse the same OpenClaw client and session policy layer.
3. Compare against LiveKit on:
   - latency
   - interruptibility
   - setup friction
   - code complexity
   - provider flexibility
   - frontend complexity
4. Decide whether Pipecat becomes:
   - an experimental backend
   - a recommended alternate backend
   - or a research branch only
5. Publish benchmark findings.

### Deliverables

- Pipecat evaluation report
- prototype adapter or rejection memo

### Exit criteria

- evidence-based decision on Pipecat, not vibes

## Detailed MVP build order

This is the strictest step-by-step sequence to follow.

### Step 1
Create the repo skeleton and baseline docs.

### Step 2
Port config loading and environment validation into the new project.

### Step 3
Port the OpenClaw agent/session mapping logic.

### Step 4
Create the minimal auth/session layer.

### Step 5
Create the LiveKit runtime adapter with the smallest working path.

### Step 6
Implement token issuance and room/session creation.

### Step 7
Build a minimal frontend that can:
- select agent
- connect
- mute
- disconnect
- show current state

### Step 8
Verify real browser-to-OpenClaw speech round-trip.

### Step 9
Add logs, health checks, and failure messages.

### Step 10
Write first-run install docs from scratch using a clean machine mindset.

### Step 11
Remove accidental complexity discovered during documentation.

### Step 12
Tag the first MVP release.

## Suggested initial issue breakdown

### Epic 1, foundation
- repo bootstrap
- config model
- ADRs
- README

### Epic 2, OpenClaw bridge
- gateway client
- agent resolution
- model policy
- session strategy

### Epic 3, LiveKit runtime
- adapter
- token issuance
- worker lifecycle
- transport config

### Epic 4, frontend
- shell UI
- auth state
- agent picker
- connect/disconnect/mute
- transcript/activity strip

### Epic 5, reliability
- health endpoint
- structured logs
- startup checks
- troubleshooting docs

### Epic 6, deployment
- local dev guide
- Tailscale guide
- reverse proxy guide
- containerization follow-up

### Epic 7, research follow-up
- runtime seam hardening
- Pipecat adapter spike
- benchmark report

## Acceptance criteria for MVP

The MVP is done only when all of the following are true:

1. A user with an existing OpenClaw instance can install the project with documented steps.
2. The app can authenticate the user or clearly run in an explicit demo mode.
3. The user can choose an allowed OpenClaw agent.
4. The user can start a voice session from a browser.
5. Speech reaches OpenClaw and responses return as audio.
6. Disconnect, reconnect, and mute work reliably.
7. Logs are good enough to diagnose the top 5 expected failures.
8. The README does not require private tribal knowledge.

## Post-MVP roadmap

After MVP, the order should be:

1. stability and docs
2. deployment polish
3. runtime seam cleanup
4. Pipecat experimental backend
5. optional advanced features like telephony, transcripts, and analytics

## Things to explicitly avoid

- building full backend abstraction before the LiveKit MVP works
- supporting too many STT/TTS providers on day one
- making public reverse proxy deployment the default getting-started path
- coupling the project too tightly to one personal infra layout
- trying to merge into OpenClaw core before the standalone project proves itself

## Final phase recommendation

If execution discipline matters, follow this exact rule:

- **MVP first, on LiveKit**
- **hardening second**
- **abstraction third**
- **Pipecat fourth**

That order preserves speed without painting the project into a corner.