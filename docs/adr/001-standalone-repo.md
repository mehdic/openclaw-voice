# ADR-001: Standalone Repo First

## Status: Accepted

## Context:

The project needs to move quickly from concept to a usable public artifact. Placing the work inside OpenClaw core would increase coordination cost, broaden the review surface, and make it harder to validate the product independently.

## Decision:

Build `openclaw-voice` as a standalone repository first rather than starting inside OpenClaw core.

## Consequences:

- Positive: the project can ship faster and iterate on its own cadence
- Positive: the scope stays narrow and easier to evaluate with real users
- Positive: value can be proven before any upstreaming discussion
- Negative: some integration points must be documented more carefully across repo boundaries
- Negative: eventual upstream adoption, if desired, may require a later migration step
