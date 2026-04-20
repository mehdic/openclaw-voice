# Contributing

Thanks for contributing to `openclaw-voice`.

## Development setup

```bash
git clone https://github.com/mehdic/openclaw-voice.git
cd openclaw-voice
cp env.example .env
# Edit .env with your OpenClaw URL, LiveKit keys, and ElevenLabs key

# With uv (recommended)
uv sync
uv run python -m openclaw_voice

# Or with pip
pip install -e ".[dev]"
python -m openclaw_voice
```

## Pull requests

- Use clear, descriptive PR titles
- Reference the related issue number when one exists
- Keep changes scoped to a single concern when practical
- Update docs when behavior, setup, or architecture decisions change

## Code style

- Use `ruff` for linting and formatting checks
- Keep lines at 120 characters or fewer
- Follow the existing project structure and naming patterns

## Testing

```bash
pytest
```

- Run tests before opening a pull request
- Add or update tests when changing behavior
- Prefer focused tests close to the code you changed
