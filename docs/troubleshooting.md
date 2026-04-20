# Troubleshooting

## Common issues

### Microphone access denied

- Browser permission prompts were dismissed or blocked.
- The page is not running from a secure context. Most browsers require `https://` or `http://localhost` for microphone access.
- Check the site permissions in the browser and allow microphone access, then reconnect.

### CORS or mixed-origin failures

- Keep the browser-facing app on the same origin as the Flask server when possible.
- If you add a reverse proxy, make sure it forwards `/api/*` to Flask without changing origin unexpectedly.
- Avoid mixing `https://` pages with `http://` upstream URLs.

### WebRTC connectivity problems

- Corporate VPNs, mobile networks, and strict firewalls often block direct ICE paths.
- Verify that the configured LiveKit deployment is reachable from the client device.
- If sessions connect intermittently, TURN availability is the first thing to verify.

### STT model download or startup delay

- `faster-whisper` model loading can take time on first run.
- Larger models increase memory use and cold-start latency.
- If startup fails, verify local disk space and that the selected model size is available for the host architecture.

### LiveKit connection failure

- Confirm `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET`.
- Make sure the browser can reach the `LIVEKIT_URL` endpoint directly.
- Check that generated room names and tokens are being returned from `/api/token` without auth errors.

## Log interpretation

- Each web request is logged with method, path, status, and duration in milliseconds.
- Worker logs identify the selected agent, session room, and any received shutdown signal.
- Repeated request failures with very short durations usually indicate input validation or auth problems.
- Longer request durations point to upstream latency between Flask and an external dependency such as OpenClaw or LiveKit.

## Known limitations

- Demo mode is intentionally permissive and should not be treated as access control.
- The frontend is a single static page and does not implement reconnect orchestration beyond basic failure handling.
- The worker and Flask server share one process entrypoint, so a fatal runtime issue can impact both surfaces.
- Local STT performance depends heavily on host CPU, memory, and model size.
