# ADR-002: Use LiveKit for MVP

## Status: Accepted

## Context:

The MVP needs a practical real-time voice backend that works well locally and has a credible path to production. The project also benefits from using technology that already aligns with prior implementation experience.

## Decision:

Use LiveKit as the voice backend for the MVP.

## Consequences:

- Positive: it builds on a battle-tested local implementation that already proved the core flow
- Positive: it provides production-grade WebRTC transport for browser voice sessions
- Positive: its room and session model fits the product shape well
- Positive: the Python SDK is strong and matches the rest of the stack
- Negative: it is heavier than the most minimal transport options
- Negative: TURN setup and operational details add deployment complexity
