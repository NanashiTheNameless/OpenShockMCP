from __future__ import annotations

import ipaddress
import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]

from . import __version__

DEFAULT_BASE_URL = "https://api.openshock.app"
DEFAULT_TIMEOUT = 15
DEFAULT_USER_AGENT = f"OpenShockMCP/{__version__}"
DEFAULT_MAX_INTENSITY = 100
DEFAULT_MAX_DURATION_MS = 65535
DEFAULT_TRANSPORT = "stdio"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_PATH = "/mcp"


class ConfigError(ValueError):
    """Raised when local configuration is invalid."""


@dataclass(frozen=True)
class OpenShockConfig:
    api_key: str | None
    base_url: str
    timeout: int
    user_agent: str
    max_intensity: int
    max_duration_ms: int
    require_confirmation: bool
    config_path: str | None

    def sanitized(self) -> dict[str, object]:
        return {
            "config_path": self.config_path,
            "api_key_configured": bool(self.api_key),
            "base_url": self.base_url,
            "timeout": self.timeout,
            "user_agent": self.user_agent,
            "max_intensity": self.max_intensity,
            "max_duration_ms": self.max_duration_ms,
            "require_confirmation": self.require_confirmation,
        }


@dataclass(frozen=True)
class ServerConfig:
    transport: str
    host: str
    port: int
    path: str
    json_response: bool


@dataclass(frozen=True)
class AppConfig:
    openshock: OpenShockConfig
    server: ServerConfig


@dataclass(frozen=True)
class AutoConfigResult:
    path: Path | None
    created: bool
    ready: bool


def load_config(path: str | os.PathLike[str] | None = None) -> OpenShockConfig:
    return load_app_config(path).openshock


def auto_configure(path: str | os.PathLike[str] | None = None) -> AutoConfigResult:
    if path is not None or _env_path():
        return AutoConfigResult(path=None, created=False, ready=True)

    local_path = Path.cwd() / "openshock-mcp.toml"
    if local_path.exists():
        return AutoConfigResult(path=local_path, created=False, ready=True)

    config_path = default_config_path()
    if config_path.exists():
        return AutoConfigResult(path=config_path, created=False, ready=True)

    api_key = os.environ.get("OPENSHOCK_API_KEY", "").strip()
    try:
        config_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        _write_new_config(config_path, api_key=api_key or "your-api-key")
    except OSError as exc:
        raise ConfigError(f"could not create config file {config_path}: {exc}") from exc
    return AutoConfigResult(path=config_path, created=True, ready=bool(api_key))


def load_app_config(path: str | os.PathLike[str] | None = None) -> AppConfig:
    config_path = resolve_config_path(path)
    data = _read_config(
        config_path,
        explicit=path is not None or _env_path() is not None,
    )
    openshock = _section(data, "openshock")
    server = _section(data, "server")
    safety = _section(data, "safety")

    return AppConfig(
        openshock=OpenShockConfig(
            api_key=_string_value(openshock, "api_key", "OPENSHOCK_API_KEY"),
            base_url=_string_value(
                openshock,
                "base_url",
                "OPENSHOCK_BASE_URL",
                DEFAULT_BASE_URL,
            ).rstrip(" /"),
            timeout=_int_value(
                openshock,
                "timeout",
                "OPENSHOCK_TIMEOUT",
                DEFAULT_TIMEOUT,
                minimum=1,
            ),
            user_agent=_string_value(
                {},
                "user_agent",
                "OPENSHOCK_USER_AGENT",
                DEFAULT_USER_AGENT,
            ),
            max_intensity=_int_value(
                safety,
                "max_intensity",
                "OPENSHOCK_MCP_MAX_INTENSITY",
                DEFAULT_MAX_INTENSITY,
                minimum=0,
                maximum=100,
            ),
            max_duration_ms=_int_value(
                safety,
                "max_duration_ms",
                "OPENSHOCK_MCP_MAX_DURATION_MS",
                DEFAULT_MAX_DURATION_MS,
                minimum=300,
                maximum=65535,
            ),
            require_confirmation=_bool_value(
                safety,
                "require_confirmation",
                "OPENSHOCK_MCP_REQUIRE_CONFIRMATION",
                True,
            ),
            config_path=str(config_path) if config_path and config_path.exists() else None,
        ),
        server=ServerConfig(
            transport=_string_value(
                server,
                "transport",
                "OPENSHOCK_MCP_TRANSPORT",
                DEFAULT_TRANSPORT,
            ),
            host=_string_value(server, "host", "OPENSHOCK_MCP_HOST", DEFAULT_HOST),
            port=_int_value(
                server,
                "port",
                "OPENSHOCK_MCP_PORT",
                DEFAULT_PORT,
                minimum=1,
                maximum=65535,
            ),
            path=normalize_http_path(
                _string_value(server, "path", "OPENSHOCK_MCP_PATH", DEFAULT_PATH)
            ),
            json_response=_bool_value(
                server,
                "json_response",
                "OPENSHOCK_MCP_JSON_RESPONSE",
                False,
            ),
        ),
    )


def default_config_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home and config_home.strip():
        return Path(config_home).expanduser() / "openshock-mcp" / "config.toml"

    system = platform.system()
    if system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata and appdata.strip():
            return Path(appdata).expanduser() / "openshock-mcp" / "config.toml"
        return Path.home() / "AppData" / "Roaming" / "openshock-mcp" / "config.toml"

    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "openshock-mcp" / "config.toml"

    return Path.home() / ".config" / "openshock-mcp" / "config.toml"


def resolve_config_path(path: str | os.PathLike[str] | None = None) -> Path | None:
    if path is not None:
        return Path(path).expanduser()

    env_path = _env_path()
    if env_path:
        return Path(env_path).expanduser()

    local_path = Path.cwd() / "openshock-mcp.toml"
    if local_path.exists():
        return local_path
    return default_config_path()


def require_api_key(config: OpenShockConfig) -> str:
    if not config.api_key:
        path = config.config_path or str(default_config_path())
        raise ConfigError(f"OpenShock API key missing; set openshock.api_key in {path}")
    return config.api_key


def require_confirmation(config: OpenShockConfig, confirm: bool) -> None:
    if config.require_confirmation and not confirm:
        raise ConfigError("action requires confirm=true")


def validate_action_limits(config: OpenShockConfig, intensity: int, duration: int) -> None:
    if intensity < 0 or intensity > 100:
        raise ConfigError("intensity must be between 0 and 100")
    if intensity > config.max_intensity:
        raise ConfigError(f"intensity {intensity} exceeds max_intensity={config.max_intensity}")
    if duration < 300 or duration > 65535:
        raise ConfigError("duration must be between 300 and 65535 milliseconds")
    if duration > config.max_duration_ms:
        raise ConfigError(f"duration {duration} exceeds max_duration_ms={config.max_duration_ms}")


def validate_loopback_host(host: str) -> str:
    normalized = host.strip()
    if not normalized:
        raise ConfigError("HTTP host must not be empty")

    lowered = normalized.lower()
    if lowered == "localhost":
        return "localhost"

    address_text = lowered
    if address_text.startswith("[") and address_text.endswith("]"):
        address_text = address_text[1:-1]

    try:
        address = ipaddress.ip_address(address_text)
    except ValueError as exc:
        raise ConfigError(
            "HTTP host must be loopback-only: use localhost, 127.0.0.1, or ::1"
        ) from exc

    if not address.is_loopback:
        raise ConfigError(
            f"refusing non-loopback HTTP host {host!r}; use 127.0.0.1, localhost, or ::1"
        )
    return normalized


def normalize_http_path(path: str) -> str:
    normalized = path.strip() or DEFAULT_PATH
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized


def _read_config(path: Path | None, *, explicit: bool) -> dict[str, Any]:
    if path is None:
        return {}
    if not path.exists():
        if explicit:
            raise ConfigError(f"config file not found: {path}")
        return {}
    try:
        with path.open("rb") as file:
            data = tomllib.load(file)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"config file must contain TOML tables: {path}")
    return data


def _env_path() -> str | None:
    env_path = os.environ.get("OPENSHOCK_MCP_CONFIG")
    if env_path and env_path.strip():
        return env_path.strip()
    return None


def _write_new_config(path: Path, *, api_key: str) -> None:
    content = _render_config(api_key=api_key)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        return
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write(content)


def _render_config(*, api_key: str) -> str:
    return f"""[server]
transport = "{DEFAULT_TRANSPORT}"
host = "{DEFAULT_HOST}"
port = {DEFAULT_PORT}
path = "{DEFAULT_PATH}"
json_response = false

[openshock]
api_key = "{_toml_string(api_key)}"
base_url = "{DEFAULT_BASE_URL}"
timeout = {DEFAULT_TIMEOUT}

[safety]
max_intensity = {DEFAULT_MAX_INTENSITY}
max_duration_ms = {DEFAULT_MAX_DURATION_MS}
require_confirmation = true
"""


def _toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"[{name}] must be a TOML table")
    return value


def _string_value(
    section: dict[str, Any],
    key: str,
    env_name: str,
    default: str | None = None,
) -> str | None:
    env_value = os.environ.get(env_name)
    if env_value is not None and env_value.strip() != "":
        return env_value.strip()

    value = section.get(key)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ConfigError(f"{key} must be a string")
    stripped = value.strip()
    return stripped if stripped else default


def _int_value(
    section: dict[str, Any],
    key: str,
    env_name: str,
    default: int,
    *,
    minimum: int,
    maximum: int | None = None,
) -> int:
    env_value = os.environ.get(env_name)
    if env_value is not None and env_value.strip() != "":
        try:
            value = int(env_value)
        except ValueError as exc:
            raise ConfigError(f"{env_name} must be an integer") from exc
    else:
        raw = section.get(key, default)
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise ConfigError(f"{key} must be an integer")
        value = raw

    if value < minimum:
        raise ConfigError(f"{key} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ConfigError(f"{key} must be <= {maximum}")
    return value


def _bool_value(
    section: dict[str, Any],
    key: str,
    env_name: str,
    default: bool,
) -> bool:
    env_value = os.environ.get(env_name)
    if env_value is not None and env_value.strip() != "":
        normalized = env_value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise ConfigError(f"{env_name} must be true or false")

    value = section.get(key, default)
    if not isinstance(value, bool):
        raise ConfigError(f"{key} must be true or false")
    return value
