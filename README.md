# OpenShock MCP

[![PyPI - Version](https://img.shields.io/pypi/v/openshock-mcp)](https://pypi.org/project/openshock-mcp/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/openshock-mcp)](https://pypi.org/project/openshock-mcp/)
[![PyPI - Implementation](https://img.shields.io/pypi/implementation/openshock-mcp)](https://pypi.org/project/openshock-mcp/)
[![PyPI - Types](https://img.shields.io/pypi/types/openshock-mcp)](https://pypi.org/project/openshock-mcp/)

[![Tests](https://github.com/NanashiTheNameless/OpenShockMCP/workflows/Test/badge.svg)](https://github.com/NanashiTheNameless/OpenShockMCP/actions/workflows/test.yml)

Loopback-only MCP server for OpenShock.

It exposes OpenShock devices and shockers as MCP tools through Python and
[Nanashi-OpenShockPY](https://github.com/NanashiTheNameless/OpenShockPY).

This server is meant to run on the same machine as your MCP client. It should
not be reachable from other devices.

## Liability Waiver

Read this before pressing buttons you might later pretend were "just testing".

**This software sends real commands to real hardware.** If you call `shock`,
`vibrate`, or `beep`, devices receive that action. This project does not detect
sarcasm, hesitation, or regret.

By using this project, you agree that:

- You are fully responsible for setup, configuration, and usage.
- You only use it with informed consent and lawful, ethical intent.
- You leave confirmation safeguards enabled unless you intentionally accept the risk.
- You understand there is no undo for actions already sent to hardware.
- You understand "I did not think it would actually do that" is not a bug report.

Short version: tool execute command. Consequences belong to operator.

## Quick Start

1. Install:

```bash
pipx install --force 'git+https://github.com/NanashiTheNameless/OpenShockMCP.git@main'
```

2. First run with your API key to generate config and start the server:

```bash
OPENSHOCK_API_KEY="your-api-key" openshock-mcp
```

3. Point your MCP client to `openshock-mcp` (stdio is the default and recommended transport).

If you prefer the full setup details, continue below.

## Requirements

- Python 3.10 or newer
- `pipx`
- `git`, because OpenShockPY installs from GitHub `main`
- An OpenShock API key

Dependencies:

```text
mcp>=1.27.0
Nanashi-OpenShockPY @ git+https://github.com/NanashiTheNameless/OpenShockPY.git@main
```

## Installation

Install from GitHub (default):

```bash
pipx install git+https://github.com/NanashiTheNameless/OpenShockMCP.git@main
```

Also available on PyPI:

```bash
pipx install openshock-mcp
```

Install a specific tag or commit:

```bash
pipx install "git+https://github.com/NanashiTheNameless/OpenShockMCP.git@v0.0.0.1"
```

For local development from a checkout:

```bash
pipx install --editable /path/to/OpenShockMCP
```

Check install:

```bash
openshock-mcp --version
```

Expected version:

```text
0.0.0.1
```

## First Run And Config Creation

The server uses a TOML config file. If no config exists, `openshock-mcp` creates
one automatically in the normal per-user config directory for your OS:

```text
Windows: %APPDATA%\openshock-mcp\config.toml
macOS:   ~/Library/Application Support/openshock-mcp/config.toml
Linux:   ~/.config/openshock-mcp/config.toml
Other:   ~/.config/openshock-mcp/config.toml
```

If `OPENSHOCK_API_KEY` is set during first run, the generated config includes it
and the server starts:

```bash
OPENSHOCK_API_KEY="your-api-key" openshock-mcp
```

If no API key is available, the server creates a template config and exits. Edit
`openshock.api_key`, then run it again.

## Configuration

### Default Config File

Generated config contents:

```toml
[server]
transport = "stdio"
host = "127.0.0.1"
port = 8000
path = "/mcp"
json_response = false

[openshock]
api_key = "your-api-key"
base_url = "https://api.openshock.app"
timeout = 15

[safety]
max_intensity = 100
max_duration_ms = 65535
require_confirmation = true
```

### Config Lookup Order

Config lookup order:

1. `--config /path/to/config.toml`
2. `$OPENSHOCK_MCP_CONFIG`
3. `./openshock-mcp.toml`
4. OS user config path

On Unix-like systems, `$XDG_CONFIG_HOME/openshock-mcp/config.toml` is used before
`~/.config/openshock-mcp/config.toml` when `XDG_CONFIG_HOME` is set.

### Environment Variable Overrides

Environment variables can override matching config values for automation.
`OPENSHOCK_USER_AGENT` is env-only; User-Agent is not written to config files.

```text
OPENSHOCK_API_KEY
OPENSHOCK_BASE_URL
OPENSHOCK_TIMEOUT
OPENSHOCK_USER_AGENT
OPENSHOCK_MCP_MAX_INTENSITY
OPENSHOCK_MCP_MAX_DURATION_MS
OPENSHOCK_MCP_REQUIRE_CONFIRMATION
OPENSHOCK_MCP_TRANSPORT
OPENSHOCK_MCP_HOST
OPENSHOCK_MCP_PORT
OPENSHOCK_MCP_PATH
OPENSHOCK_MCP_JSON_RESPONSE
OPENSHOCK_MCP_CONFIG
```

`openshock-mcp.toml` is ignored by git so local secrets do not get committed.
`openshock-mcp.example.toml` is a safe template.

## Running The Server

### Stdio (Recommended)

`stdio` is the default and recommended transport for desktop MCP clients. It
does not open a network port.

Do not use `stdio` as an interactive terminal program. MCP clients launch it and
send JSON-RPC over stdin. If you run `openshock-mcp` directly in a terminal, it
prints usage guidance instead of starting the protocol stream.

With explicit config:

```bash
openshock-mcp --config ~/.config/openshock-mcp/config.toml
```

On Windows PowerShell, pass a Windows path:

```powershell
openshock-mcp --config "$env:APPDATA\openshock-mcp\config.toml"
```

Claude Desktop style config:

```json
{
  "mcpServers": {
    "openshock": {
      "command": "openshock-mcp",
      "args": ["--config", "/home/YOUR_USER/.config/openshock-mcp/config.toml"]
    }
  }
}
```

### HTTP (Only If Your Client Requires It)

Use streamable HTTP only when your MCP client needs an HTTP MCP endpoint. The
server refuses non-loopback hosts such as `0.0.0.0` and LAN IP addresses.

```bash
openshock-mcp \
  --transport streamable-http \
  --host 127.0.0.1 \
  --port 8765 \
  --config ~/.config/openshock-mcp/config.toml
```

MCP endpoint:

```text
http://127.0.0.1:8765/mcp
```

On startup, the server prints sanitized startup info to stderr:

```text
openshock-mcp 0.0.0.1 starting
transport: streamable-http
mcp endpoint: http://127.0.0.1:8765/mcp
config: /path/to/config.toml
api key configured: yes
safety: max_intensity=100, max_duration_ms=65535, require_confirmation=true
```

Stdio startup info also goes to stderr so stdout stays reserved for MCP JSON-RPC.

This is allowed:

```bash
openshock-mcp --transport http --host 127.0.0.1
```

This is rejected:

```bash
openshock-mcp --transport http --host 0.0.0.0
```

## Tools

Read-only tools:

- `openshock_status`: show sanitized config status. Does not reveal API key.
- `list_devices`: list OpenShock devices.
- `get_device`: get one device by ID.
- `list_shockers`: list shockers, optionally filtered by device ID.
- `get_shocker`: get one shocker by ID.

Action tools:

- `shock`: shock one shocker, or use `shocker_id="all"`.
- `vibrate`: vibrate one shocker, or use `shocker_id="all"`.
- `beep`: beep one shocker, or use `shocker_id="all"`.
- `stop`: stop one shocker, or use `shocker_id="all"`.

`shock`, `vibrate`, and `beep` require `confirm=true` by default. Keep
`require_confirmation = true` unless you understand the risk. `stop` does not
require confirmation.

Typical action arguments:

```json
{
  "shocker_id": "your-shocker-id",
  "intensity": 25,
  "duration": 1000,
  "exclusive": false,
  "confirm": true
}
```

Limits:

- `intensity`: `0` to `100`, also capped by `max_intensity`
- `duration`: `300` to `65535` ms, also capped by `max_duration_ms`

## Security Model (Local Only)

- `stdio` opens no network listener.
- HTTP mode only accepts loopback bind hosts: `127.0.0.1`, `localhost`, or `::1`.
- Non-loopback hosts are rejected before startup.
- The MCP SDK enables DNS rebinding protection for loopback hosts.
- API keys are read from local config or environment only.

## Troubleshooting

### `OpenShock API key missing`

Set `[openshock].api_key` in your config file, or set `OPENSHOCK_API_KEY`.

### `config file not found`

The path passed to `--config` must exist. If you want default lookup, omit
`--config`.

### `refusing non-loopback HTTP host`

Use `127.0.0.1`, `localhost`, or `::1`. This project intentionally does not bind
to LAN or public interfaces.

### `git` not found during install

Install `git`. OpenShockPY is installed from GitHub `main`.

## License

PolyForm Noncommercial License 1.0.0. See [LICENSE.md](LICENSE.md).
