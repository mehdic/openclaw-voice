# ADR-004: OpenClaw Is the Brain

## Status: Accepted

## Context:

The project exists to add a voice layer to OpenClaw, not to recreate OpenClaw features in a second system. Duplicating agent logic would create drift, confusion, and extra maintenance burden.

## Decision:

Keep all intelligence in OpenClaw. This project handles transport, speech-to-text, text-to-speech, and browser UI only. It does not duplicate agent logic, memory, or tool execution.

## Consequences:

- Positive: OpenClaw remains the single source of truth for agent behavior
- Positive: the integration stays thinner and easier to reason about
- Positive: improvements in OpenClaw agent logic automatically benefit voice sessions
- Negative: the project depends on the OpenClaw gateway API being sufficient for voice use cases
- Negative: some voice-specific UX needs must be solved without moving business logic into this repo
