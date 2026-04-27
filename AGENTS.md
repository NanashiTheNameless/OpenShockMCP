# AGENTS.md

Guide for coding agents working in this repository.

## Scope

- Repository: OpenShockMCP
- Language: Python (>=3.10)
- Package entrypoint: `nanashi-openshock-mcp` -> `openshock_mcp.cli:main`
- Primary source directory: `src/openshock_mcp/`
- Tests directory: `tests/`

## Default Response Mode

Use the `caveman` skill by default for agent responses.

Local copy in this repository:

- `third_party/caveman/SKILL.md`
- `third_party/caveman/LICENSE`
- `third_party/caveman/NOTICE.md`

- Default intensity: `full`.
- Keep technical content accurate; remove filler.
- If user asks for normal style (for example: `normal mode` or `stop caveman`), switch to normal style.
- For safety-critical warnings, irreversible actions, or multi-step instructions where terse style may cause confusion, use clear normal wording for that part, then resume caveman mode.
- Code, commit messages, and file edits should follow normal repository conventions unless explicitly requested otherwise.

## Project Intent

This project is a loopback-only MCP server for OpenShock.

Critical behavior to preserve:

- `stdio` is the default transport.
- HTTP transport must remain loopback-only.
- Action tools (`shock`, `vibrate`, `beep`) must keep explicit confirmation safeguards.
- API keys must never be printed or exposed in tool responses.

## Repository Map

- `src/openshock_mcp/cli.py`: CLI parsing, startup flow, transport handling.
- `src/openshock_mcp/config.py`: Config loading, env overrides, validation, defaults.
- `src/openshock_mcp/server.py`: MCP tool registration and OpenShock client integration.
- `tests/test_config.py`: Config and safety validation tests.
- `tests/test_cli.py`: CLI helper behavior tests.
- `.github/workflows/test.yml`: CI test workflow.
- `.github/workflows/python-publish.yml`: release publish workflow (depends on `test.yml`).

## Setup

Use a virtual environment or pipx-managed environment for development.

Typical local setup:

```bash
python -m pip install --upgrade pip
pip install -e .[dev]
```

Run tests:

```bash
pytest -q
```

## Coding Rules

- Keep changes small and targeted.
- Preserve existing public CLI options unless a task explicitly requires change.
- Prefer explicit validation and clear error messages (`ConfigError`) for user-facing failures.
- Keep defaults documented and aligned across code and `README.md`.
- Do not add network exposure beyond loopback.
- Do not log secrets.

## MCP-Specific Guardrails

When changing server behavior:

- Keep MCP tools deterministic and JSON-serializable.
- Keep `openshock_status` sanitized (no raw secrets).
- Keep `stop` callable without confirmation.
- Keep confirmation required by default for `shock`, `vibrate`, and `beep`.
- Preserve action limit checks (`max_intensity`, `max_duration_ms`, hard bounds).

## Testing Expectations

At minimum, run:

```bash
pytest -q
```

If behavior changes around transport/config/safety, add or update tests in:

- `tests/test_config.py`
- `tests/test_cli.py`

## Documentation Expectations

If you change any of the following, update `README.md` in the same change:

- install commands
- config keys or defaults
- environment variable names
- transport behavior
- tool names or arguments

## Release Notes

- Publishing uses `.github/workflows/python-publish.yml`.
- Publish workflow calls reusable tests in `.github/workflows/test.yml`.
- Keep reusable workflow compatibility (`workflow_call`) intact.

## Non-Goals

Unless explicitly requested, avoid:

- changing license text
- changing package name or CLI command name
- broad refactors unrelated to the requested task
- introducing unrelated dependencies
