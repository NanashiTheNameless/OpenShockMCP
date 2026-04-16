from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from OpenShockPY import OpenShockClient

try:
    from OpenShockPY import OpenShockPYError as OpenShockLibraryError
except ImportError:
    from OpenShockPY import OpenShockError as OpenShockLibraryError

from .config import (
    ConfigError,
    OpenShockConfig,
    load_config,
    require_api_key,
    require_confirmation,
    validate_action_limits,
)

ControlType = Literal["Shock", "Vibrate", "Sound", "Stop"]


def build_server(
    *,
    config_path: str | None = None,
    host: str = "127.0.0.1",
    port: int = 8000,
    streamable_http_path: str = "/mcp",
    json_response: bool = False,
) -> FastMCP:
    mcp = FastMCP(
        "OpenShock MCP",
        instructions=(
            "Use OpenShock tools only after explicit user intent. "
            "Shock, vibrate, and beep are physical side effects."
        ),
        host=host,
        port=port,
        streamable_http_path=streamable_http_path,
        json_response=json_response,
    )

    @mcp.tool()
    def openshock_status() -> dict[str, object]:
        """Return sanitized OpenShock MCP configuration."""
        return load_config(config_path).sanitized()

    @mcp.tool()
    def list_devices() -> dict[str, Any]:
        """List OpenShock devices for the configured API key."""
        with _client(load_config(config_path)) as client:
            return _ok(client.list_devices())

    @mcp.tool()
    def get_device(device_id: str) -> dict[str, Any]:
        """Get one OpenShock device by device ID."""
        with _client(load_config(config_path)) as client:
            return _ok(client.get_device(device_id))

    @mcp.tool()
    def list_shockers(device_id: str | None = None) -> dict[str, Any]:
        """List OpenShock shockers, optionally only for one device ID."""
        with _client(load_config(config_path)) as client:
            return _ok(client.list_shockers(device_id=device_id))

    @mcp.tool()
    def get_shocker(shocker_id: str) -> dict[str, Any]:
        """Get one OpenShock shocker by shocker ID."""
        with _client(load_config(config_path)) as client:
            return _ok(client.get_shocker(shocker_id))

    @mcp.tool()
    def shock(
        shocker_id: str,
        intensity: int = 50,
        duration: int = 1000,
        exclusive: bool = False,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Shock one OpenShock shocker, or pass shocker_id='all' for all shockers."""
        config = load_config(config_path)
        require_confirmation(config, confirm)
        validate_action_limits(config, intensity, duration)
        return _control(config, shocker_id, "Shock", intensity, duration, exclusive)

    @mcp.tool()
    def vibrate(
        shocker_id: str,
        intensity: int = 50,
        duration: int = 1000,
        exclusive: bool = False,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Vibrate one OpenShock shocker, or pass shocker_id='all' for all shockers."""
        config = load_config(config_path)
        require_confirmation(config, confirm)
        validate_action_limits(config, intensity, duration)
        return _control(config, shocker_id, "Vibrate", intensity, duration, exclusive)

    @mcp.tool()
    def beep(
        shocker_id: str,
        duration: int = 300,
        exclusive: bool = False,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Beep one OpenShock shocker, or pass shocker_id='all' for all shockers."""
        config = load_config(config_path)
        require_confirmation(config, confirm)
        validate_action_limits(config, 0, duration)
        return _control(config, shocker_id, "Sound", 0, duration, exclusive)

    @mcp.tool()
    def stop(shocker_id: str) -> dict[str, Any]:
        """Stop one OpenShock shocker, or pass shocker_id='all' for all shockers."""
        config = load_config(config_path)
        return _control(config, shocker_id, "Stop", 0, 300, False)

    return mcp


@contextmanager
def _client(config: OpenShockConfig) -> Iterator[OpenShockClient]:
    api_key = require_api_key(config)
    client = OpenShockClient(
        api_key=api_key,
        base_url=config.base_url,
        timeout=config.timeout,
        user_agent=config.user_agent,
    )
    try:
        yield client
    except OpenShockLibraryError as exc:
        raise ConfigError(str(exc)) from exc
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()
        else:
            session = getattr(client, "_session", None)
            if session is not None:
                session.close()


def _control(
    config: OpenShockConfig,
    shocker_id: str,
    control_type: ControlType,
    intensity: int,
    duration: int,
    exclusive: bool,
) -> dict[str, Any]:
    with _client(config) as client:
        if shocker_id.lower() == "all":
            send_all = getattr(client, "send_action_all", None)
            if callable(send_all):
                response = send_all(control_type, intensity, duration, exclusive)
            else:
                shocker_ids = _list_shocker_ids(client)
                if not shocker_ids:
                    raise ConfigError("no shockers found")
                response = [
                    client.send_action(shocker, control_type, intensity, duration, exclusive)
                    for shocker in shocker_ids
                ]
        else:
            response = client.send_action(shocker_id, control_type, intensity, duration, exclusive)
    return _ok(
        response,
        action=control_type,
        target=shocker_id,
        intensity=intensity,
        duration=duration,
        exclusive=exclusive,
    )


def _ok(response: Any, **extra: Any) -> dict[str, Any]:
    payload = {"ok": True, "response": response}
    payload.update(extra)
    return payload


def _list_shocker_ids(client: OpenShockClient) -> list[str]:
    return _extract_shocker_ids(client.list_shockers())


def _extract_shocker_ids(payload: Any) -> list[str]:
    seen: set[str] = set()
    shocker_ids: list[str] = []

    def add(value: Any) -> None:
        if isinstance(value, str) and value not in seen:
            seen.add(value)
            shocker_ids.append(value)

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            shockers = value.get("shockers")
            if isinstance(shockers, list):
                for shocker in shockers:
                    visit(shocker)
                return
            add(value.get("id"))
            return
        if isinstance(value, list):
            for item in value:
                visit(item)

    if isinstance(payload, dict):
        if "data" in payload:
            visit(payload["data"])
        if "shockers" in payload:
            visit(payload["shockers"])
    else:
        visit(payload)

    return shocker_ids
