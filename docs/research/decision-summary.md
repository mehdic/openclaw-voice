# Decision summary

## Recommended direction

Build the new OSS project by **productizing the existing LiveKit-based implementation first**.

Do **not** start with a full Pipecat rewrite.

## Why

- the current LiveKit implementation already solved the hardest OpenClaw-specific problems
- it is closer to a real product than a framework demo
- it gives the fastest path to a usable MVP
- it preserves hard-won lessons from real deployment and voice UX tuning
- Pipecat remains a strong future backend option, but not the best first shipping move

## Architecture stance

Use this sequence:

1. ship a standalone repo
2. build MVP on LiveKit
3. harden install and operations
4. introduce a thin runtime adapter seam
5. evaluate Pipecat as an optional backend

## What the project should be

A **quick-install browser voice layer for OpenClaw**, not a giant voice platform and not a fork of OpenClaw core.

## MVP definition

- browser UI
- auth or explicit demo mode
- allowed agent selection
- LiveKit transport
- OpenClaw as the brain
- one good STT path
- one good TTS path
- simple local setup

## Future path

After MVP:

- improve reliability and deployment polish
- keep the runtime boundary clean
- spike a Pipecat adapter
- compare based on latency, complexity, and install friction

## Bottom line

**Start from what already works. Then make it clean, simple, and open source.**

That is the highest-probability path to a project people will actually use.