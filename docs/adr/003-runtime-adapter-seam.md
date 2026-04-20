# ADR-003: Thin Runtime Adapter Seam

## Status: Accepted

## Context:

The MVP is shipping on LiveKit, but future backend comparison may still be valuable. Without a clear boundary, the codebase could become tightly coupled to one runtime and harder to benchmark or evolve.

## Decision:

Design a thin runtime adapter boundary so an alternative runtime such as Pipecat can be added later. Keep the seam narrow and avoid broad abstraction work before the MVP ships.

## Consequences:

- Positive: the project avoids unnecessary lock-in to a single runtime
- Positive: future benchmarking between LiveKit and Pipecat remains possible
- Positive: the MVP code can stay focused on a small, well-defined integration surface
- Negative: even a narrow seam introduces some design overhead up front
- Negative: over-abstracting too early would slow delivery, so discipline is required to keep the boundary small
