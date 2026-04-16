"""Loopback-only MCP server for OpenShock."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

try:
	import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
	import tomli as tomllib  # type: ignore[no-redef]


def _version_from_pyproject() -> str:
	pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
	with pyproject_path.open("rb") as file:
		data = tomllib.load(file)
	project = data.get("project", {})
	value = project.get("version")
	if not isinstance(value, str) or not value.strip():
		raise RuntimeError("project.version missing in pyproject.toml")
	return value.strip()


try:
	__version__ = version("openshock-mcp")
except PackageNotFoundError:  # pragma: no cover - local source checkout fallback
	__version__ = _version_from_pyproject()
