"""OpenClaw Voice process entrypoint."""

from __future__ import annotations

import logging
import threading

from .app.config import get_config
from .app.server import create_app
from .runtime.livekit.worker import main as run_worker

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Configure structured application logging."""

    logging.basicConfig(
        level=logging.INFO,
        format=(
            '{"timestamp":"%(asctime)s","level":"%(levelname)s","module":"%(name)s",'
            '"message":"%(message)s"}'
        ),
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        force=True,
    )


def _run_web_server() -> None:
    """Run the Flask web server."""

    cfg = get_config()
    app = create_app()
    app.run(host="0.0.0.0", port=cfg.server.web_port, debug=False, use_reloader=False)


def main() -> None:
    """Run the web server and LiveKit worker process."""

    import sys

    _configure_logging()

    # LiveKit CLI expects a subcommand (dev/start/connect). Default to 'dev' if none given.
    if len(sys.argv) < 2 or sys.argv[1] not in ("dev", "start", "connect", "download-files", "console"):
        sys.argv = [sys.argv[0], "dev"]

    web_thread = threading.Thread(target=_run_web_server, name="openclaw-voice-web", daemon=True)
    web_thread.start()
    logger.info("Started Flask web server thread")
    run_worker()


if __name__ == "__main__":
    main()
