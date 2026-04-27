"""Loopback-only MCP server for OpenShock."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

try:
	import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
	import tomli as tomllib  # type: ignore[no-redef]


def _version_from_pyproject() -> str | None:
	pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
	if not pyproject_path.exists():
		return None
	with pyproject_path.open("rb") as file:
		data = tomllib.load(file)
	project = data.get("project", {})
	value = project.get("version")
	if not isinstance(value, str) or not value.strip():
		raise RuntimeError("project.version missing in pyproject.toml")
	return value.strip()


_pyproject_version = _version_from_pyproject()
if _pyproject_version is not None:
	__version__ = _pyproject_version
else:
	try:
		__version__ = version("nanashi-openshock-mcp")
	except PackageNotFoundError as exc:  # pragma: no cover - unexpected runtime state
		raise RuntimeError("could not determine package version") from exc
