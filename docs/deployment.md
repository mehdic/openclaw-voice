# Deployment

## Local development

### Prerequisites

- Python 3.11 or newer
- A virtual environment tool such as `venv`
- LiveKit credentials if you want full voice sessions
- OpenClaw reachable from the same machine or network

### Setup

```bash
git clone <repo-url>
cd openclaw-voice
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp env.example .env
```

Set the values in `.env` for your environment:

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `OPENCLAW_URL`
- `OPENCLAW_TOKEN`
- `ELEVEN_API_KEY`
- `AUTH_MODE`

Run the app:

```bash
python -m openclaw_voice
```

The Flask UI listens on `0.0.0.0:${WEB_PORT:-7890}`. The LiveKit worker starts in the same process.

## Tailscale and LAN access

The web server already binds to `0.0.0.0`, so non-localhost access mostly depends on the URLs you advertise and the network path:

- Set `WEB_PORT` to the port you want exposed.
- Open that port on the host firewall.
- Use a reachable host name or IP when visiting the UI from another device.
- If OpenClaw is not on the same host, set `OPENCLAW_URL` to a LAN or Tailscale address instead of `localhost`.
- If the LiveKit deployment is self-hosted or private, make sure client devices can reach the `LIVEKIT_URL` endpoint directly.

If you keep `OPENCLAW_URL` or other upstreams on `localhost`, only the local machine will be able to use them.

## Reverse proxy

For public HTTPS exposure, place a reverse proxy in front of Flask. Example `nginx` configuration:

```nginx
server {
    listen 443 ssl http2;
    server_name voice.example.com;

    ssl_certificate /etc/letsencrypt/live/voice.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/voice.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:7890;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Notes:

- WebSocket upgrade headers are required for browser and LiveKit-related realtime traffic.
- TLS termination should happen at the proxy or upstream load balancer.
- TURN is not proxied through Flask. If clients sit behind restrictive NATs, use a LiveKit deployment with TURN support configured and reachable over the public internet.
- If you deploy behind a path prefix, update the proxy rules carefully because the frontend expects root-relative API paths such as `/api/session`.

## Security posture

- The default auth mode is `demo`. That is suitable for local development only.
- In `demo` mode, every browser session is treated as authenticated and receives the configured default agent access.
- For non-local environments, set `AUTH_MODE=google`, configure `GOOGLE_CLIENT_ID`, and define `AUTHORIZED_EMAILS`.
- Keep `LIVEKIT_API_SECRET`, `OPENCLAW_TOKEN`, `SESSION_SECRET`, and provider API keys out of source control. Load them from `.env`, a secret manager, or deployment-specific environment variables.
- Treat public exposure as high risk until Google auth, HTTPS, and upstream access controls are in place.
- Do not expose an OpenClaw instance or gateway that trusts localhost-only assumptions to an untrusted network.
