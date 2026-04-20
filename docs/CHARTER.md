# Project Charter

## What

`openclaw-voice` is a lightweight, self-hostable browser voice layer for OpenClaw. It adds real-time voice interaction on top of existing OpenClaw agents without changing how those agents think or operate.

## Who

This project is for OpenClaw users who want voice interaction with their agents from a browser, using infrastructure they can run and control themselves.

## What it does

- Provides browser-based voice sessions for OpenClaw agents
- Handles voice transport, speech-to-text, text-to-speech, and a thin user interface
- Connects to OpenClaw through the gateway API rather than embedding agent logic locally

## What it does not solve

- It is not a general voice framework
- It is not a replacement for OpenClaw core voice work
- It is not a telephony product in v1

## Relationship to OpenClaw core

`openclaw-voice` is a standalone companion to OpenClaw. It consumes the OpenClaw gateway API and does not patch OpenClaw internals.

## Success criteria

- An OpenClaw user can install the project and talk to an existing agent from a browser
- The integration remains thin, understandable, and easy to operate
- The project proves practical value before any upstream discussion with OpenClaw core
