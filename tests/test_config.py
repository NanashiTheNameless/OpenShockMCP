import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from openshock_mcp.config import (
    ConfigError,
    auto_configure,
    default_config_path,
    load_app_config,
    normalize_http_path,
    validate_loopback_host,
)


class ConfigTests(unittest.TestCase):
    def test_loopback_hosts_allowed(self):
        for host in ["127.0.0.1", "127.15.0.9", "::1", "[::1]", "localhost"]:
            with self.subTest(host=host):
                self.assertEqual(validate_loopback_host(host), host)

    def test_non_loopback_hosts_rejected(self):
        for host in ["0.0.0.0", "192.168.1.10", "example.com", ""]:
            with self.subTest(host=host):
                with self.assertRaises(ConfigError):
                    validate_loopback_host(host)

    def test_normalize_http_path(self):
        self.assertEqual(normalize_http_path("mcp"), "/mcp")
        self.assertEqual(normalize_http_path("/openshock"), "/openshock")
        self.assertEqual(normalize_http_path(""), "/mcp")

    def test_load_config_file(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                """
[server]
transport = "streamable-http"
host = "127.0.0.1"
port = 9001
path = "mcp"
json_response = true

[openshock]
api_key = "secret"
base_url = "https://api.openshock.example"
timeout = 10

[safety]
max_intensity = 20
max_duration_ms = 1000
require_confirmation = false
""".strip(),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {}, clear=True):
                config = load_app_config(path)

            self.assertEqual(config.server.transport, "streamable-http")
            self.assertEqual(config.server.port, 9001)
            self.assertEqual(config.server.path, "/mcp")
            self.assertTrue(config.server.json_response)
            self.assertEqual(config.openshock.api_key, "secret")
            self.assertEqual(config.openshock.user_agent, "OpenShockMCP/0.0.1.0")
            self.assertEqual(config.openshock.max_intensity, 20)
            self.assertFalse(config.openshock.require_confirmation)

    def test_explicit_missing_config_rejected(self):
        with TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {}, clear=True):
                with self.assertRaises(ConfigError):
                    load_app_config(Path(tmp) / "missing.toml")

    def test_auto_configure_creates_template_without_key(self):
        with TemporaryDirectory() as tmp:
            config_home = Path(tmp) / "config-home"
            with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(config_home)}, clear=True):
                result = auto_configure()

            self.assertTrue(result.created)
            self.assertFalse(result.ready)
            self.assertIsNotNone(result.path)
            self.assertTrue(result.path.exists())
            text = result.path.read_text(encoding="utf-8")
            self.assertIn('api_key = "your-api-key"', text)

    def test_auto_configure_uses_env_api_key(self):
        with TemporaryDirectory() as tmp:
            config_home = Path(tmp) / "config-home"
            with patch.dict(
                "os.environ",
                {"XDG_CONFIG_HOME": str(config_home), "OPENSHOCK_API_KEY": "secret"},
                clear=True,
            ):
                result = auto_configure()
                config = load_app_config()

            self.assertTrue(result.created)
            self.assertTrue(result.ready)
            self.assertEqual(config.openshock.api_key, "secret")

    def test_default_config_path_uses_windows_appdata(self):
        with TemporaryDirectory() as tmp:
            appdata = Path(tmp) / "AppData" / "Roaming"
            with patch.dict("os.environ", {"APPDATA": str(appdata)}, clear=True):
                with patch("openshock_mcp.config.platform.system", return_value="Windows"):
                    path = default_config_path()

            self.assertEqual(path, appdata / "openshock-mcp" / "config.toml")

    def test_default_config_path_uses_macos_application_support(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            with patch.dict("os.environ", {}, clear=True):
                with patch("openshock_mcp.config.platform.system", return_value="Darwin"):
                    with patch("openshock_mcp.config.Path.home", return_value=home):
                        path = default_config_path()

            self.assertEqual(
                path,
                home / "Library" / "Application Support" / "openshock-mcp" / "config.toml",
            )


if __name__ == "__main__":
    unittest.main()
