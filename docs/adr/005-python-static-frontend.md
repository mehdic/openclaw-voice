# ADR-005: Python Backend with Static Frontend

## Status: Accepted

## Context:

The initial stack should fit the surrounding OpenClaw ecosystem, reuse proven implementation patterns, and keep setup simple for early adopters.

## Decision:

Use a Python backend with a static JavaScript frontend for the initial architecture.

## Consequences:

- Positive: the backend matches the OpenClaw ecosystem and contributor expectations
- Positive: it aligns with the existing implementation and reduces translation work
- Positive: a static frontend avoids introducing a separate frontend build step for MVP
- Negative: the frontend will be intentionally simple and less opinionated than a larger SPA stack
- Negative: richer client-side behavior may require revisiting the approach later if the UI grows substantially
