from __future__ import annotations

import argparse
import asyncio
import sys

from . import __version__
from .config import (
    ConfigError,
    auto_configure,
    load_app_config,
    normalize_http_path,
    validate_loopback_host,
)


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    try:
        auto_config = auto_configure(args.config)
        if auto_config.created:
            print(f"nanashi-openshock-mcp: created config file: {auto_config.path}", file=sys.stderr)
            if not auto_config.ready:
                print(
                    "nanashi-openshock-mcp: edit openshock.api_key in that file, then run again",
                    file=sys.stderr,
                )
                return 2

        app_config = load_app_config(args.config)
        transport = args.transport or app_config.server.transport
        transport = "streamable-http" if transport == "http" else transport
        host = args.host or app_config.server.host
        port = args.port if args.port is not None else app_config.server.port
        path = normalize_http_path(args.path or app_config.server.path)
        json_response = args.json_response or app_config.server.json_response

        if transport not in {"stdio", "streamable-http"}:
            raise ConfigError("transport must be stdio or streamable-http")
        if transport == "stdio" and _stdio_is_interactive():
            _print_stdio_terminal_help(args.config)
            return 0

        host = validate_loopback_host(host) if transport != "stdio" else "127.0.0.1"
        from .server import build_server

        server = build_server(
            config_path=args.config,
            host=host,
            port=port,
            streamable_http_path=path,
            json_response=json_response,
        )
    except ConfigError as exc:
        print(f"nanashi-openshock-mcp: {exc}", file=sys.stderr)
        return 2

    _print_startup_info(
        transport=transport,
        host=host,
        port=port,
        path=path,
        config_path=app_config.openshock.config_path,
        api_key_configured=bool(app_config.openshock.api_key),
        max_intensity=app_config.openshock.max_intensity,
        max_duration_ms=app_config.openshock.max_duration_ms,
        require_confirmation=app_config.openshock.require_confirmation,
    )

    if transport == "stdio":
        _run_server(server, transport="stdio")
    else:
        _run_server(server, transport="streamable-http")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nanashi-openshock-mcp",
        description="Loopback-only MCP server for OpenShock.",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "http"],
        default=None,
        help="MCP transport. Overrides config.",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="HTTP bind host. Must be loopback. Overrides config.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="HTTP bind port. Overrides config.",
    )
    parser.add_argument(
        "--path",
        default=None,
        help="Streamable HTTP MCP path. Overrides config.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to config TOML. Defaults to nanashi-openshock-mcp.toml or user config dir.",
    )
    parser.add_argument(
        "--json-response",
        action="store_true",
        help="Use JSON responses for streamable HTTP.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit.",
    )
    return parser


def _stdio_is_interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _print_stdio_terminal_help(config_path: str | None) -> None:
    config_hint = f" --config {config_path}" if config_path else ""
    print(
        "nanashi-openshock-mcp is configured for stdio MCP transport.\n"
        "Stdio mode is launched by an MCP client and expects JSON-RPC on stdin.\n"
        "Do not run it interactively in a terminal.\n\n"
        "Use one of these instead:\n"
        f"  - Add command to your MCP client: nanashi-openshock-mcp{config_hint}\n"
        f"  - Run local HTTP mode: nanashi-openshock-mcp --transport http{config_hint}\n"
        "  - Show version: nanashi-openshock-mcp --version",
        file=sys.stderr,
    )


def _print_startup_info(
    *,
    transport: str,
    host: str,
    port: int,
    path: str,
    config_path: str | None,
    api_key_configured: bool,
    max_intensity: int,
    max_duration_ms: int,
    require_confirmation: bool,
) -> None:
    if transport == "streamable-http":
        endpoint = _http_endpoint(host, port, path)
    else:
        endpoint = "stdio (launched by MCP client; no network address)"

    print(
        "\n".join(
            [
                f"nanashi-openshock-mcp {__version__} starting",
                f"transport: {transport}",
                f"mcp endpoint: {endpoint}",
                f"config: {config_path or 'none'}",
                f"api key configured: {'yes' if api_key_configured else 'no'}",
                (
                    "safety: "
                    f"max_intensity={max_intensity}, "
                    f"max_duration_ms={max_duration_ms}, "
                    f"require_confirmation={str(require_confirmation).lower()}"
                ),
            ]
        ),
        file=sys.stderr,
    )


def _http_endpoint(host: str, port: int, path: str) -> str:
    normalized_host = host
    if ":" in normalized_host and not normalized_host.startswith("["):
        normalized_host = f"[{normalized_host}]"
    return f"http://{normalized_host}:{port}{path}"


def _run_server(server, *, transport: str) -> None:
    try:
        server.run(transport=transport)
    except (KeyboardInterrupt, asyncio.CancelledError):
        return


if __name__ == "__main__":
    raise SystemExit(main())
